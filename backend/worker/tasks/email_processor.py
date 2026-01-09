"""
Email processing Celery tasks.
Handles email fetching, classification, and auto-reply.
"""
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# Task 1: Fetch emails from Gmail
def fetch_and_process_emails(user_id: str, email_account_id: str, max_results: int = 5) -> dict:
    """
    Fetch emails from user's Gmail account.
    
    Process flow:
    1. Get email account from database
    2. Refresh access token if needed
    3. Fetch unread emails from Gmail
    4. Parse email metadata
    5. Store in database as EmailJob records
    6. Trigger classification task for each email
    
    Args:
        user_id: User ID
        email_account_id: Email account ID
        max_results: Maximum emails to fetch per run (default 5)
        
    Returns:
        Task result dictionary with:
        - status: 'success' or 'failed'
        - emails_fetched: Number of emails fetched from Gmail
        - emails_processed: Number of EmailJob records created
        - errors: Any errors encountered
    """
    from models import EmailAccount, EmailJob
    from database import SessionLocal
    from connectors.gmail import GmailConnector
    from security.encryption import token_encryption
    from config import settings
    
    db = SessionLocal()
    errors = []
    emails_processed = 0
    
    try:
        # Step 1: Get email account from database
        email_account = db.query(EmailAccount).filter(
            EmailAccount.id == email_account_id,
            EmailAccount.user_id == user_id,
        ).first()
        
        if not email_account:
            raise ValueError(f"Email account not found: {email_account_id}")
        
        if not email_account.is_active:
            raise ValueError(f"Email account is inactive: {email_account_id}")
        
        logger.info(f"Fetching emails for account {email_account.email}")
        
        # Step 2: Decrypt access token
        try:
            access_token = token_encryption.decrypt(email_account.access_token_encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt access token: {e}")
            raise ValueError("Failed to decrypt access token")
        
        # Step 3: Check if token expired and refresh if needed
        if email_account.token_expires_at and datetime.utcnow() >= email_account.token_expires_at:
            logger.info(f"Token expired, refreshing for {email_account.email}")
            try:
                if not email_account.refresh_token_encrypted:
                    raise ValueError("No refresh token available")
                
                refresh_token = token_encryption.decrypt(email_account.refresh_token_encrypted)
                
                gmail = GmailConnector(
                    client_id=settings.gmail_client_id,
                    client_secret=settings.gmail_client_secret,
                    redirect_uri=settings.gmail_redirect_uri,
                )
                
                token_data = gmail.refresh_access_token(refresh_token)
                access_token = token_data["access_token"]
                
                # Update database with new token
                email_account.access_token_encrypted = token_encryption.encrypt(access_token)
                email_account.token_expires_at = datetime.fromisoformat(
                    token_data["expires_at"].replace('Z', '+00:00')
                )
                db.commit()
                logger.info(f"Token refreshed successfully for {email_account.email}")
                
            except Exception as e:
                logger.error(f"Failed to refresh token: {e}")
                raise ValueError(f"Token refresh failed: {str(e)}")
        
        # Step 4: Create Gmail connector and fetch emails
        gmail = GmailConnector(
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
            redirect_uri=settings.gmail_redirect_uri,
        )
        
        emails = gmail.fetch_emails(
            access_token=access_token,
            max_results=max_results,
            query="is:unread",
        )
        
        emails_fetched = len(emails)
        logger.info(f"Fetched {emails_fetched} unread emails from {email_account.email}")
        
        # Step 5: Store emails as EmailJob records
        for email_data in emails:
            try:
                # Check if this email already exists
                existing = db.query(EmailJob).filter(
                    EmailJob.email_account_id == email_account_id,
                    EmailJob.email_id == email_data["message_id"],
                ).first()
                
                if existing:
                    logger.debug(f"Email {email_data['message_id']} already exists, skipping")
                    continue
                
                # Create EmailJob record
                email_job = EmailJob(
                    user_id=user_id,
                    email_account_id=email_account_id,
                    email_id=email_data["message_id"],
                    subject=email_data.get("subject", ""),
                    sender=email_data.get("from", ""),
                    body=email_data.get("body", "")[:5000],  # Truncate to 5000 chars
                    is_processed=False,
                )
                
                db.add(email_job)
                db.flush()
                emails_processed += 1
                logger.debug(f"Created EmailJob {email_job.id} for {email_job.subject}")
                
                # Step 6: Trigger classification task
                from backend.worker.tasks.classifier import classify_email
                classify_email.apply_async(
                    args=(email_job.id,),
                    kwargs={"user_context": {"user_id": user_id}},
                )
                
                # Step 7: Trigger recommendation generation (will run after classification)
                from backend.worker.tasks.recommender import generate_recommendation
                generate_recommendation.apply_async(
                    args=(email_job.id,),
                    kwargs={"user_context": {"user_id": user_id}},
                    countdown=2,  # Wait 2 seconds for classification to complete
                )
            except Exception as e:
                logger.error(f"Failed to process email {email_data.get('message_id')}: {e}")
                errors.append(f"Email processing failed: {str(e)}")
                db.rollback()
                continue
        
        # Commit all EmailJob records
        db.commit()
        
        # Update email account's last_sync timestamp
        email_account.last_sync = datetime.utcnow()
        db.commit()
        
        logger.info(f"Successfully processed {emails_processed} emails for {email_account.email}")
        
        return {
            "status": "success",
            "emails_fetched": emails_fetched,
            "emails_processed": emails_processed,
            "errors": errors,
        }
        
    except Exception as e:
        logger.error(f"Error in fetch_and_process_emails: {e}")
        return {
            "status": "failed",
            "emails_fetched": 0,
            "emails_processed": 0,
            "errors": [str(e)],
        }
    
    finally:
        db.close()


# Task 2: Classify email
def classify_email(email_job_id: str) -> dict:
    """
    Classify a single email using LLM.
    
    Process flow:
    1. Get email job from database
    2. Use EmailClassifier to classify
    3. Update email_job with classification
    4. Check if auto-reply rules match
    5. If match: trigger auto-reply task
    6. If important: flag the email
    
    Args:
        email_job_id: Email job ID
        
    Returns:
        Task result dictionary with:
        - status: 'success' or 'failed'
        - classification: Classification result
        - auto_reply_triggered: Whether auto-reply was sent
    """
    # To be implemented in Phase B
    # Flow:
    # 1. Get EmailJob from DB
    # 2. Create EmailClassifier
    # 3. Call classifier.classify()
    # 4. Update EmailJob with classification
    # 5. If classification matches rule: call send_auto_reply.delay()
    # 6. If is_flagged: call flag_email.delay()
    raise NotImplementedError("To be implemented in Phase B")


# Task 3: Send auto-reply
def send_auto_reply(email_job_id: str, auto_reply_rule_id: str) -> dict:
    """
    Send automatic reply to email.
    
    Process flow:
    1. Get email job and auto-reply rule from database
    2. Get email account and refresh token if needed
    3. Generate reply text (using template or LLM)
    4. Send reply via Gmail
    5. Mark email as replied
    6. Log action
    
    Args:
        email_job_id: Email job ID
        auto_reply_rule_id: Auto-reply rule ID
        
    Returns:
        Task result dictionary with:
        - status: 'success' or 'failed'
        - reply_message_id: Gmail message ID of sent reply
        - reply_text: Text of reply sent
    """
    # To be implemented in Phase B
    # Flow:
    # 1. Get EmailJob and AutoReplyRule from DB
    # 2. Generate reply (template-based)
    # 3. Get access token (decrypt)
    # 4. Create GmailConnector
    # 5. Call connector.send_email()
    # 6. Update EmailJob.auto_reply_sent = True
    # 7. Log action
    raise NotImplementedError("To be implemented in Phase B")


# Task 4: Flag email
def flag_email(email_job_id: str) -> dict:
    """
    Flag/star email in Gmail.
    
    Args:
        email_job_id: Email job ID
        
    Returns:
        Task result with success status
    """
    # To be implemented in Phase B
    # Flow:
    # 1. Get EmailJob from DB
    # 2. Get access token
    # 3. Create GmailConnector
    # 4. Call connector.star_email()
    # 5. Update EmailJob.is_flagged = True
    raise NotImplementedError("To be implemented in Phase B")


# Task 5: Data analysis
def analyze_data_file(job_id: str, file_path: str, analysis_type: str, user_prompt: str) -> dict:
    """
    Perform data analysis on uploaded file.
    
    Process flow:
    1. Get data analysis job from database
    2. Download file from S3
    3. Create DataAnalyzer
    4. Perform analysis based on type
    5. Store results in database
    6. Update job status to completed
    
    Args:
        job_id: Data analysis job ID
        file_path: S3 file path
        analysis_type: Type of analysis ('summary', 'insights', 'forecast', etc.)
        user_prompt: User's analysis request
        
    Returns:
        Task result dictionary with:
        - status: 'success' or 'failed'
        - analysis_type: Type of analysis performed
        - result: Analysis results
        - execution_time: Time taken
    """
    # To be implemented in Phase B
    # Flow:
    # 1. Get DataAnalysisJob from DB
    # 2. Update status to 'processing'
    # 3. Download file from S3 (S3DataHandler)
    # 4. Create DataAnalyzer
    # 5. Call analyzer.upload_and_analyze()
    # 6. Update DataAnalysisJob with results
    # 7. Update status to 'completed'
    raise NotImplementedError("To be implemented in Phase B")


# Task 6: Schedule periodic email sync
def scheduled_email_sync(user_id: str) -> dict:
    """
    Periodic task to sync emails for a user.
    
    Triggered by Celery Beat on a schedule (e.g., every 15 minutes).
    
    Args:
        user_id: User ID
        
    Returns:
        Task result
    """
    # To be implemented in Phase B
    # Flow:
    # 1. Get all email accounts for user
    # 2. For each account: call fetch_and_process_emails.delay()
    # 3. Log results
    raise NotImplementedError("To be implemented in Phase B")


# Task helper: Get current user from ID
def get_user_by_id(user_id: str):
    """Helper to get user from database."""
    from models import User
    from database import SessionLocal

    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()


# Task helper: Get email account with token refresh
def get_email_account_with_token(email_account_id: str):
    """
    Get email account and ensure token is valid.
    
    Refreshes token if expired.
    """
    from models import EmailAccount
    from database import SessionLocal
    from datetime import datetime

    db = SessionLocal()
    try:
        account = db.query(EmailAccount).filter(EmailAccount.id == email_account_id).first()
        
        if not account:
            raise ValueError(f"Email account not found: {email_account_id}")
        
        # Check if token expired
        if account.token_expires_at and datetime.utcnow() >= account.token_expires_at:
            logger.info(f"Token expired for account {email_account_id}, refreshing...")
            # Call refresh logic here
            # This will be implemented in Phase B
            pass
        
        return account
    finally:
        db.close()
