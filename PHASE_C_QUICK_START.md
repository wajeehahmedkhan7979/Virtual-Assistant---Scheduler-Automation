# Quick Start: Email Classification

## Prerequisites

1. **Python 3.13** with venv activated
2. **PostgreSQL** running and configured
3. **Redis** running (for Celery)
4. **OpenAI API Key** (required for classification)

## Setup (5 minutes)

### 1. Environment Variables

Add to `.env`:

```env
OPENAI_API_KEY=sk-your-key-here

# Optional (have defaults)
EMAIL_CATEGORIES='{"important": "Time-sensitive or high-priority emails", "actionable": "Contains tasks or action items", "followup": "Requires a follow-up response", "informational": "For reference only", "spam": "Unsolicited or unwanted messages", "promotional": "Marketing or promotional content"}'
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.6
```

### 2. Start Services

```bash
# Terminal 1: FastAPI server
python -m uvicorn backend.main:app --reload

# Terminal 2: Celery worker (required for async classification)
celery -A backend.worker.celery_app worker -l info

# Terminal 3: Redis (if not running as service)
redis-server
```

## Testing Classification

### Option 1: Manual Test (No Database)

```bash
curl -X POST http://localhost:8000/api/v1/email/classify-manual \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "boss@company.com",
    "subject": "Urgent: Q4 Report Due",
    "body": "Please submit the quarterly financial report by EOD today."
  }'
```

Expected response:

```json
{
  "email_job_id": "manual",
  "category": "important",
  "confidence": 0.95,
  "explanation": "Urgent business email from senior manager with tight deadline"
}
```

### Option 2: Fetch & Auto-Classify

```bash
# This will fetch emails from Gmail and automatically classify them
curl -X POST http://localhost:8000/api/v1/email/fetch \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email_account_id": "account-uuid"}'
```

### Option 3: Query Classified Emails

```bash
# Get all important emails
curl "http://localhost:8000/api/v1/email/classified?category=important" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get high-confidence classifications (90%+)
curl "http://localhost:8000/api/v1/email/classified?min_confidence=90" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Run Tests

### All Classification Tests

```bash
pytest backend/tests/test_email_classification.py -v
```

### Specific Test

```bash
pytest backend/tests/test_email_classification.py::TestEmailClassifierClassification::test_classify_important_email -v
```

### Coverage Report

```bash
pytest backend/tests/test_email_classification.py --cov=backend.llm --cov=backend.worker.tasks.classifier
```

## Verify Installation

Check that all components are working:

```bash
python -c "
from backend.llm.classifier import EmailClassifier
from backend.worker.tasks.classifier import classify_email
from backend.api.email import router

classifier = EmailClassifier()
print(f'✓ EmailClassifier initialized')
print(f'✓ Categories loaded: {list(classifier.categories.keys())}')
print(f'✓ Confidence threshold: {classifier.confidence_threshold}')
"
```

## Common Tasks

### Classify All Unclassified Emails

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import EmailJob
from backend.worker.tasks.classifier import classify_emails_batch
from backend.config import settings

engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)
session = Session()

# Get unclassified emails
unclassified = session.query(EmailJob).filter(
    EmailJob.classification.is_(None)
).all()

# Classify them
email_ids = [email.id for email in unclassified]
if email_ids:
    task = classify_emails_batch.apply_async(args=(email_ids,))
    result = task.get()  # Wait for completion
    print(f"Classified {result['successful']} emails")
```

### Query Classified Emails

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import EmailJob
from backend.config import settings

engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)
session = Session()

# Get important emails with high confidence
important = session.query(EmailJob).filter(
    EmailJob.classification == "important",
    EmailJob.classification_confidence >= 90
).all()

for email in important:
    print(f"{email.subject}: {email.classification} ({email.classification_confidence}%)")
    print(f"  {email.classification_explanation}")
```

## Customizing Categories

To change classification categories:

1. Edit `.env` EMAIL_CATEGORIES JSON
2. Restart FastAPI server
3. EmailClassifier will load new categories automatically

Example: Add "urgent" category

```env
EMAIL_CATEGORIES='{"important": "Time-sensitive or high-priority emails", "urgent": "Requires immediate action within hours", "actionable": "Contains tasks or action items", "followup": "Requires a follow-up response", "informational": "For reference only", "spam": "Unsolicited or unwanted messages", "promotional": "Marketing or promotional content"}'
```

## Troubleshooting

### Classification returns all "informational"

1. Check OPENAI_API_KEY is valid: `echo $OPENAI_API_KEY`
2. Check Celery worker is running
3. Check logs: `journalctl -u celery` or terminal where Celery runs

### "OpenAI API key not configured" error

```bash
# Make sure OPENAI_API_KEY is set
export OPENAI_API_KEY=sk-...

# Verify it's set
echo $OPENAI_API_KEY
```

### Celery tasks not executing

1. Ensure Redis is running: `redis-cli ping` (should return PONG)
2. Ensure Celery worker is started: `celery -A backend.worker.celery_app worker -l info`
3. Check worker logs for errors

### Database errors

1. Ensure PostgreSQL is running
2. Check DATABASE_URL in .env
3. Run migrations: `alembic upgrade head` (if using alembic)

## Architecture

```
Email Flow:
1. Email fetched from Gmail via Gmail API
2. EmailJob record created in database
3. Celery task: classify_email triggered
4. EmailClassifier calls OpenAI via LangChain
5. Results stored in EmailJob (category, confidence, explanation)
6. Emails queryable via API with filtering
```

## API Endpoints Reference

| Endpoint                        | Method | Purpose                        |
| ------------------------------- | ------ | ------------------------------ |
| `/api/v1/email/jobs/{id}`       | GET    | Get email details              |
| `/api/v1/email/classify`        | POST   | Trigger classification task    |
| `/api/v1/email/classify-batch`  | POST   | Batch classify multiple emails |
| `/api/v1/email/classify-manual` | POST   | Test classify without database |
| `/api/v1/email/classified`      | GET    | Get classified emails          |

## Next Steps

1. **Test with real Gmail account**

   - Create EmailAccount via OAuth
   - Fetch emails
   - Verify classification works

2. **Monitor classification accuracy**

   - Check confidence scores
   - Look for patterns in misclassifications
   - Consider adjusting OpenAI temperature/model

3. **Prepare for Phase C Step 2**
   - Auto-reply rule implementation
   - Email operations (archive, label)
   - User feedback loop

## Resources

- **Main Documentation**: [PHASE_C_EMAIL_CLASSIFICATION.md](PHASE_C_EMAIL_CLASSIFICATION.md)
- **Implementation Summary**: [PHASE_C_IMPLEMENTATION_SUMMARY.md](PHASE_C_IMPLEMENTATION_SUMMARY.md)
- **Code**: [backend/llm/classifier.py](backend/llm/classifier.py)
- **Tests**: [backend/tests/test_email_classification.py](backend/tests/test_email_classification.py)
- **API**: [backend/api/email.py](backend/api/email.py)
