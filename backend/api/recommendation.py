"""
Action recommendation API endpoints.
Provides endpoints to view and manage action recommendations.
"""
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.dependencies import get_db, get_current_user
from backend.models import User, EmailJob, ActionRecommendation
from backend.worker.tasks.recommender import generate_recommendation, generate_recommendations_batch
from backend.llm.rule_engine import create_rule_engine

router = APIRouter(prefix="/api/v1/recommendation", tags=["recommendations"])


# ============================================================================
# Request/Response Models
# ============================================================================

class RecommendedAction(BaseModel):
    """A recommended action."""
    
    type: str
    description: str
    priority: int
    reason: str
    
    class Config:
        from_attributes = True


class ActionRecommendationResponse(BaseModel):
    """Action recommendation response model."""
    
    id: str
    email_job_id: str
    rule_names: Optional[str]
    recommended_actions: List[dict]
    safety_flags: Optional[List[str]]
    confidence_score: Optional[int]
    reasoning: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class GenerateRecommendationRequest(BaseModel):
    """Request to generate recommendation for email."""
    
    email_job_id: str


class GenerateRecommendationsRequest(BaseModel):
    """Request to generate recommendations for multiple emails."""
    
    email_job_ids: List[str]


class ReviewRecommendationRequest(BaseModel):
    """Request to review/accept/reject recommendation."""
    
    status: str  # accepted, rejected
    rejection_reason: Optional[str] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/email/{email_job_id}", response_model=Optional[ActionRecommendationResponse])
async def get_recommendation(
    email_job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Optional[ActionRecommendationResponse]:
    """
    Get recommendation for an email.
    
    Args:
        email_job_id: Email job ID
        
    Returns:
        Recommendation details or null if none exists
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
    
    recommendation = db.query(ActionRecommendation).filter(
        ActionRecommendation.email_job_id == email_job_id,
        ActionRecommendation.user_id == current_user.id,
    ).first()
    
    if recommendation:
        return ActionRecommendationResponse.from_orm(recommendation)
    return None


@router.post("/generate", response_model=dict)
async def generate_recommendation_endpoint(
    request: GenerateRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Generate recommendation for an email.
    
    Submits async task to evaluate rules and create recommendation.
    
    Args:
        request: Email job ID to generate recommendation for
        
    Returns:
        Task ID for tracking
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
    
    # Check if already has recommendation
    existing = db.query(ActionRecommendation).filter(
        ActionRecommendation.email_job_id == request.email_job_id
    ).first()
    
    if existing:
        return {
            "email_job_id": request.email_job_id,
            "recommendation_id": existing.id,
            "status": "exists",
            "message": "Recommendation already exists",
        }
    
    # Submit recommendation task
    task = generate_recommendation.apply_async(
        args=(request.email_job_id,),
        kwargs={"user_context": {"user_id": current_user.id}},
    )
    
    return {
        "task_id": task.id,
        "email_job_id": request.email_job_id,
        "status": "submitted",
    }


@router.post("/generate-batch", response_model=dict)
async def generate_recommendations_endpoint(
    request: GenerateRecommendationsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Generate recommendations for multiple emails.
    
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
    
    # Submit batch recommendation task
    task = generate_recommendations_batch.apply_async(
        args=(request.email_job_ids,),
        kwargs={"user_context": {"user_id": current_user.id}},
    )
    
    return {
        "task_id": task.id,
        "email_count": len(request.email_job_ids),
        "status": "submitted",
    }


@router.patch("/{recommendation_id}/review", response_model=dict)
async def review_recommendation(
    recommendation_id: str,
    request: ReviewRecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Review recommendation (accept or reject).
    
    Does NOT execute actions - just tracks user feedback.
    
    Args:
        recommendation_id: ID of recommendation
        request: Review action (accepted/rejected) and optional reason
        
    Returns:
        Updated recommendation
    """
    recommendation = db.query(ActionRecommendation).filter(
        ActionRecommendation.id == recommendation_id,
        ActionRecommendation.user_id == current_user.id,
    ).first()
    
    if not recommendation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found",
        )
    
    # Update status
    if request.status == "accepted":
        recommendation.status = "accepted"
        recommendation.accepted_at = datetime.utcnow()
        recommendation.rejected_at = None
        recommendation.rejection_reason = None
    elif request.status == "rejected":
        recommendation.status = "rejected"
        recommendation.rejected_at = datetime.utcnow()
        recommendation.rejection_reason = request.rejection_reason
        recommendation.accepted_at = None
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be 'accepted' or 'rejected'.",
        )
    
    db.commit()
    
    return {
        "id": recommendation.id,
        "status": recommendation.status,
        "accepted_at": recommendation.accepted_at,
        "rejected_at": recommendation.rejected_at,
    }


@router.get("/", response_model=List[ActionRecommendationResponse])
async def list_recommendations(
    status_filter: Optional[str] = None,
    min_confidence: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ActionRecommendationResponse]:
    """
    List recommendations for current user.
    
    Args:
        status_filter: Filter by status (generated, reviewed, accepted, rejected)
        min_confidence: Minimum confidence threshold (0-100)
        limit: Number of results (max 100)
        offset: Offset for pagination
        
    Returns:
        List of recommendations
    """
    query = db.query(ActionRecommendation).filter(
        ActionRecommendation.user_id == current_user.id,
    )
    
    if status_filter:
        query = query.filter(ActionRecommendation.status == status_filter)
    
    if min_confidence is not None:
        query = query.filter(
            ActionRecommendation.confidence_score >= min_confidence
        )
    
    recommendations = query.order_by(
        ActionRecommendation.created_at.desc()
    ).limit(min(limit, 100)).offset(offset).all()
    
    return [ActionRecommendationResponse.from_orm(r) for r in recommendations]


@router.post("/test-rules", response_model=dict)
async def test_rules(
    classification: str,
    confidence: float,
    sender: str,
    subject: str,
    body: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Test rule evaluation without saving recommendation.
    
    Useful for debugging and testing rule configurations.
    
    Args:
        classification: Email classification category
        confidence: Classification confidence (0-1)
        sender: Email sender
        subject: Email subject
        body: Email body
        
    Returns:
        Evaluation result with matched rules and actions
    """
    try:
        engine = create_rule_engine()
        
        evaluation = engine.evaluate(
            classification=classification,
            confidence=confidence,
            sender=sender,
            subject=subject,
            body=body,
        )
        
        return {
            "matched_rules": evaluation.matched_rules,
            "recommended_actions": evaluation.recommended_actions,
            "safety_flags": evaluation.safety_flags,
            "confidence_score": evaluation.confidence_score,
            "reasoning": evaluation.reasoning,
            "success": True,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rule evaluation error: {str(e)}",
        )
