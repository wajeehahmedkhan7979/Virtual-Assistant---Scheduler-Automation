"""
Celery worker configuration and task definitions.
"""
from celery import Celery
from config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "va_scheduler",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes hard limit
    task_soft_time_limit=25 * 60,  # 25 minutes soft limit
)


@celery_app.task(bind=True, max_retries=3)
def process_email(self, user_id: str, email_account_id: str):
    """
    Fetch and process emails from inbox.
    """
    try:
        logger.info(f"Processing emails for user {user_id}")
        # Implementation in Phase B
        return {"status": "success", "user_id": user_id}
    except Exception as exc:
        logger.error(f"Error processing email: {exc}")
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def send_auto_reply(self, email_job_id: str, reply_text: str):
    """
    Send auto-reply to matched email.
    """
    try:
        logger.info(f"Sending auto-reply for email job {email_job_id}")
        # Implementation in Phase B
        return {"status": "success", "email_job_id": email_job_id}
    except Exception as exc:
        logger.error(f"Error sending auto-reply: {exc}")
        self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, max_retries=3)
def analyze_data(self, job_id: str, file_path: str, prompt: str):
    """
    Perform on-demand data analysis using LLM.
    """
    try:
        logger.info(f"Starting data analysis for job {job_id}")
        # Implementation in Phase B
        return {"status": "success", "job_id": job_id}
    except Exception as exc:
        logger.error(f"Error analyzing data: {exc}")
        self.retry(exc=exc, countdown=60)


# Health check task
@celery_app.task
def health_check():
    """Celery health check task."""
    logger.info("Celery worker health check passed")
    return "pong"
