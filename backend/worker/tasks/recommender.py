"""
Celery task for generating action recommendations.
Evaluates rules against classified emails and stores recommendations.
"""
import logging
from datetime import datetime
from typing import Optional

from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.config import settings
from backend.models import EmailJob, ActionRecommendation
from backend.llm.rule_engine import create_rule_engine

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="generate_recommendation",
)
def generate_recommendation(
    self,
    email_job_id: str,
    user_context: Optional[dict] = None,
) -> dict:
    """
    Generate action recommendation for classified email.
    
    Evaluates user rules against email classification and creates
    ActionRecommendation record with suggested actions.
    
    Args:
        email_job_id: ID of EmailJob to generate recommendation for
        user_context: Optional user context with rules
        
    Returns:
        Dictionary with recommendation results:
        - email_job_id: ID of email
        - recommendation_id: ID of recommendation record
        - matched_rules: Names of matched rules
        - recommended_actions: List of suggested actions
        - confidence_score: Confidence in recommendations (0-100)
        - success: Whether generation succeeded
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
            
            # Check if email is classified
            if not email_job.classification:
                logger.warning(f"Email {email_job_id} not classified, skipping recommendation")
                return {
                    "email_job_id": email_job_id,
                    "success": False,
                    "error": "Email not classified",
                }
            
            # Check if recommendation already exists
            existing = session.query(ActionRecommendation).filter(
                ActionRecommendation.email_job_id == email_job_id
            ).first()
            
            if existing:
                logger.info(f"Recommendation already exists for email {email_job_id}")
                return {
                    "email_job_id": email_job_id,
                    "recommendation_id": existing.id,
                    "success": True,
                    "already_exists": True,
                }
            
            # Get user rules (from context or defaults)
            user_rules = None
            if user_context and "rules" in user_context:
                user_rules = user_context["rules"]
            
            # Create rule engine
            engine_instance = create_rule_engine(user_rules)
            
            # Evaluate rules
            evaluation = engine_instance.evaluate(
                classification=email_job.classification,
                confidence=(email_job.classification_confidence or 0) / 100.0,
                sender=email_job.sender or "",
                subject=email_job.subject or "",
                body=email_job.body or "",
                labels=None,  # TODO: Get from Gmail if available
            )
            
            # Create recommendation record
            recommendation = ActionRecommendation(
                user_id=email_job.user_id,
                email_job_id=email_job_id,
                rule_names=",".join(r["name"] for r in evaluation.matched_rules) if evaluation.matched_rules else None,
                recommended_actions=evaluation.recommended_actions,
                safety_flags=evaluation.safety_flags if evaluation.safety_flags else None,
                confidence_score=evaluation.confidence_score,
                reasoning=evaluation.reasoning,
                status="generated",
            )
            
            session.add(recommendation)
            session.commit()
            
            logger.info(
                f"Generated recommendation for email {email_job_id}: "
                f"{len(evaluation.recommended_actions)} actions, "
                f"confidence {evaluation.confidence_score}%"
            )
            
            return {
                "email_job_id": email_job_id,
                "recommendation_id": recommendation.id,
                "matched_rules": [r["name"] for r in evaluation.matched_rules],
                "recommended_actions": evaluation.recommended_actions,
                "confidence_score": evaluation.confidence_score,
                "success": True,
            }
            
        except Exception as e:
            logger.error(f"Error generating recommendation for {email_job_id}: {e}", exc_info=True)
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
    name="generate_recommendations_batch",
)
def generate_recommendations_batch(
    self,
    email_job_ids: list,
    user_context: Optional[dict] = None,
) -> dict:
    """
    Generate recommendations for multiple emails in batch.
    
    Args:
        email_job_ids: List of EmailJob IDs
        user_context: Optional user context with rules
        
    Returns:
        Dictionary with batch results:
        - total: Total emails processed
        - successful: Successful recommendations
        - failed: Failed recommendations
        - details: List of individual results
    """
    logger.info(f"Starting batch recommendation generation for {len(email_job_ids)} emails")
    
    results = {
        "total": len(email_job_ids),
        "successful": 0,
        "failed": 0,
        "details": [],
    }
    
    for email_job_id in email_job_ids:
        try:
            result = generate_recommendation.apply_async(
                args=(email_job_id,),
                kwargs={"user_context": user_context},
            ).get(timeout=30)
            
            results["details"].append(result)
            
            if result.get("success"):
                results["successful"] += 1
            else:
                results["failed"] += 1
                
        except Exception as e:
            logger.error(f"Failed to generate recommendation for {email_job_id}: {e}")
            results["failed"] += 1
            results["details"].append({
                "email_job_id": email_job_id,
                "success": False,
                "error": str(e),
            })
    
    logger.info(
        f"Batch recommendation generation complete: "
        f"{results['successful']}/{results['total']} successful"
    )
    
    return results
