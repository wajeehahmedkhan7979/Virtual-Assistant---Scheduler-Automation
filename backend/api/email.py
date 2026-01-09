"""
Email management API endpoints.
Provides endpoints for email operations (fetch, classify, etc).
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.dependencies import get_db, get_current_user
from backend.models import User, EmailJob, EmailAccount
from backend.worker.tasks.classifier import classify_email, classify_emails_batch
from backend.llm.classifier import EmailClassifier

router = APIRouter(prefix="/api/v1/email", tags=["email"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ClassificationResult(BaseModel):
    """Classification result for a single email."""
    
    email_job_id: str
    category: str
    confidence: float
    explanation: str
    
    class Config:
        from_attributes = True


class EmailJobResponse(BaseModel):
    """Email job response model."""
    
    id: str
    subject: Optional[str]
    sender: Optional[str]
    classification: Optional[str]
    classification_confidence: Optional[int]
    classification_explanation: Optional[str]
    is_processed: bool
    created_at: datetime
    classified_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ClassifyEmailRequest(BaseModel):
    """Request to classify a single email."""
    
    email_job_id: str


class ClassifyEmailsRequest(BaseModel):
    """Request to classify multiple emails."""
    
    email_job_ids: list[str]


class ManualClassificationRequest(BaseModel):
    """Request to classify email by content (not from database)."""
    
    sender: str
    subject: str
    body: str


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/jobs/{email_job_id}", response_model=EmailJobResponse)
async def get_email_job(
    email_job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailJobResponse:
    """
    Get email job details.
    
    Args:
        email_job_id: Email job ID
        
    Returns:
        Email job with classification results (if available)
    """
    email_job = db.query(EmailJob).filter(
        EmailJob.id == email_job_id,
        EmailJob.user_id == current_user.id,
    ).first()
    
    if not email_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email job not found",
        )
    
    return EmailJobResponse.from_orm(email_job)


@router.post("/classify", response_model=dict)
async def classify_email_endpoint(
    request: ClassifyEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Classify a single email from database.
    
    Submits a Celery task to classify the email and return task ID.
    Use the task ID to poll for results.
    
    Args:
        request: Email job ID to classify
        
    Returns:
        Task ID for tracking classification status
    """
    # Verify email exists and belongs to user
    email_job = db.query(EmailJob).filter(
        EmailJob.id == request.email_job_id,
        EmailJob.user_id == current_user.id,
    ).first()
    
    if not email_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email job not found",
        )
    
    # Submit classification task
    task = classify_email.apply_async(
        args=(request.email_job_id,),
        kwargs={"user_context": {"user_id": current_user.id}},
    )
    
    return {
        "task_id": task.id,
        "email_job_id": request.email_job_id,
        "status": "submitted",
    }


@router.post("/classify-batch", response_model=dict)
async def classify_emails_endpoint(
    request: ClassifyEmailsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Classify multiple emails in batch.
    
    Submits a Celery task to classify multiple emails.
    
    Args:
        request: List of email job IDs
        
    Returns:
        Task ID for tracking batch status
    """
    # Verify all emails exist and belong to user
    email_count = db.query(EmailJob).filter(
        EmailJob.id.in_(request.email_job_ids),
        EmailJob.user_id == current_user.id,
    ).count()
    
    if email_count != len(request.email_job_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Some email jobs not found",
        )
    
    # Submit batch classification task
    task = classify_emails_batch.apply_async(
        args=(request.email_job_ids,),
        kwargs={"user_context": {"user_id": current_user.id}},
    )
    
    return {
        "task_id": task.id,
        "email_count": len(request.email_job_ids),
        "status": "submitted",
    }


@router.post("/classify-manual", response_model=ClassificationResult)
async def classify_manual_endpoint(
    request: ManualClassificationRequest,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Classify email content directly (not from database).
    
    Useful for testing classification without storing in database.
    
    Args:
        request: Email content (sender, subject, body)
        
    Returns:
        Classification result with category, confidence, explanation
        
    Raises:
        HTTPException: If OpenAI API not configured
    """
    try:
        classifier = EmailClassifier()
        result = classifier.classify(
            sender=request.sender,
            subject=request.subject,
            body=request.body,
            user_context={"user_id": current_user.id},
        )
        
        return {
            "email_job_id": "manual",
            "category": result["category"],
            "confidence": result["confidence"],
            "explanation": result["explanation"],
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Classification service error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Classification error: {str(e)}",
        )


@router.get("/classified", response_model=list[EmailJobResponse])
async def get_classified_emails(
    category: Optional[str] = None,
    min_confidence: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailJobResponse]:
    """
    Get classified emails for current user.
    
    Args:
        category: Filter by classification category
        min_confidence: Minimum confidence percentage (0-100)
        limit: Number of results (max 100)
        offset: Offset for pagination
        
    Returns:
        List of classified emails
    """
    query = db.query(EmailJob).filter(
        EmailJob.user_id == current_user.id,
        EmailJob.classification.isnot(None),
    )
    
    if category:
        query = query.filter(EmailJob.classification == category)
    
    if min_confidence is not None:
        query = query.filter(
            EmailJob.classification_confidence >= min_confidence
        )
    
    # Order by classified_at descending, limit results
    emails = query.order_by(
        EmailJob.classified_at.desc()
    ).limit(min(limit, 100)).offset(offset).all()
    
    return [EmailJobResponse.from_orm(email) for email in emails]
