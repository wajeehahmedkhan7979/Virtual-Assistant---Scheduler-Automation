"""
Celery task for email classification.
Classifies stored emails using LLM and stores results in database.
"""
import logging
from datetime import datetime
from typing import Optional

from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import settings
from backend.models import EmailJob
from backend.llm.classifier import EmailClassifier

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="classify_email",
)
def classify_email(
    self,
    email_job_id: str,
    user_context: Optional[dict] = None,
) -> dict:
    """
    Classify an email and store results in database.
    
    Args:
        email_job_id: ID of EmailJob to classify
        user_context: Optional user context for classification
        
    Returns:
        Dictionary with classification results:
        - email_job_id: ID of classified email
        - category: Classification category
        - confidence: Confidence score (0-1)
        - explanation: Classification explanation
        - success: Whether classification succeeded
        - error: Error message (if failed)
    """
    try:
        # Initialize database session
        engine = create_engine(settings.database_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Fetch email job
            email_job = session.query(EmailJob).filter(
                EmailJob.id == email_job_id
            ).first()
            
            if not email_job:
                logger.error(f"EmailJob not found: {email_job_id}")
                return {
                    "email_job_id": email_job_id,
                    "success": False,
                    "error": "EmailJob not found",
                }
            
            # Skip if already classified
            if email_job.classification and email_job.classified_at:
                logger.info(f"Email {email_job_id} already classified, skipping")
                return {
                    "email_job_id": email_job_id,
                    "category": email_job.classification,
                    "confidence": (email_job.classification_confidence or 0) / 100.0,
                    "explanation": email_job.classification_explanation,
                    "success": True,
                    "already_classified": True,
                }
            
            # Initialize classifier
            classifier = EmailClassifier()
            
            # Classify email
            result = classifier.classify(
                sender=email_job.sender or "",
                subject=email_job.subject or "",
                body=email_job.body or "",
                user_context=user_context,
            )
            
            category = result["category"]
            confidence = result["confidence"]
            explanation = result["explanation"]
            
            # Check if confidence meets threshold
            if confidence < classifier.confidence_threshold:
                logger.warning(
                    f"Classification confidence {confidence} below threshold "
                    f"{classifier.confidence_threshold} for email {email_job_id}"
                )
            
            # Store results in database
            email_job.classification = category
            email_job.classification_confidence = int(confidence * 100)  # Store as 0-100
            email_job.classification_explanation = explanation
            email_job.classified_at = datetime.utcnow()
            
            session.commit()
            logger.info(
                f"Classified email {email_job_id}: {category} "
                f"(confidence: {confidence:.2f})"
            )
            
            return {
                "email_job_id": email_job_id,
                "category": category,
                "confidence": confidence,
                "explanation": explanation,
                "success": True,
            }
            
        except Exception as e:
            logger.error(f"Error classifying email {email_job_id}: {e}", exc_info=True)
            session.rollback()
            
            # Retry with exponential backoff
            raise self.retry(exc=e)
            
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Task error for email {email_job_id}: {e}", exc_info=True)
        return {
            "email_job_id": email_job_id,
            "success": False,
            "error": str(e),
        }


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="classify_emails_batch",
)
def classify_emails_batch(
    self,
    email_job_ids: list,
    user_context: Optional[dict] = None,
) -> dict:
    """
    Classify multiple emails in batch.
    
    Args:
        email_job_ids: List of EmailJob IDs to classify
        user_context: Optional user context
        
    Returns:
        Dictionary with batch results:
        - total: Total emails processed
        - successful: Successful classifications
        - failed: Failed classifications
        - details: List of individual results
    """
    logger.info(f"Starting batch classification of {len(email_job_ids)} emails")
    
    results = {
        "total": len(email_job_ids),
        "successful": 0,
        "failed": 0,
        "details": [],
    }
    
    for email_job_id in email_job_ids:
        try:
            result = classify_email.apply_async(
                args=(email_job_id,),
                kwargs={"user_context": user_context},
            ).get(timeout=30)  # Wait up to 30 seconds per email
            
            results["details"].append(result)
            
            if result.get("success"):
                results["successful"] += 1
            else:
                results["failed"] += 1
                
        except Exception as e:
            logger.error(f"Failed to classify email {email_job_id}: {e}")
            results["failed"] += 1
            results["details"].append({
                "email_job_id": email_job_id,
                "success": False,
                "error": str(e),
            })
    
    logger.info(
        f"Batch classification complete: "
        f"{results['successful']}/{results['total']} successful"
    )
    
    return results
