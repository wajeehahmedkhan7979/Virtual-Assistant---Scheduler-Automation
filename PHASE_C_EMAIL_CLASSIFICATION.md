# Email Classification Implementation (Phase C Step 1)

## Overview

Email classification uses LangChain + OpenAI to automatically categorize emails into user-configurable categories. Classification results are stored in the database and can be used to power filtering, routing, and other email management workflows.

## Architecture

### Components

1. **EmailClassifier** (`backend/llm/classifier.py`)

   - Loads categories from configuration
   - Uses LangChain + ChatOpenAI for LLM calls
   - Returns: category, confidence score (0-1), explanation
   - Validates responses and handles errors gracefully

2. **Celery Tasks** (`backend/worker/tasks/classifier.py`)

   - `classify_email`: Classify single email from database
   - `classify_emails_batch`: Classify multiple emails
   - Auto-triggered by `fetch_and_process_emails` task
   - Stores results back to database

3. **API Endpoints** (`backend/api/email.py`)

   - GET `/api/v1/email/jobs/{email_job_id}` - Get email details
   - POST `/api/v1/email/classify` - Trigger classification task
   - POST `/api/v1/email/classify-batch` - Batch classification
   - POST `/api/v1/email/classify-manual` - Test classification without DB
   - GET `/api/v1/email/classified` - Get classified emails

4. **Database Model** (`backend/models.py::EmailJob`)
   - `classification`: Category name (string)
   - `classification_confidence`: Confidence score 0-100 (integer)
   - `classification_explanation`: Why classified this way (text)
   - `classified_at`: Timestamp of classification

## Configuration

Email categories are configured via environment variables in `.env`:

```env
# Email classification categories (JSON)
# Each category has a name and description
EMAIL_CATEGORIES='{"important": "Time-sensitive or high-priority emails", "actionable": "Contains tasks or action items", "followup": "Requires a follow-up response", "informational": "For reference only", "spam": "Unsolicited or unwanted messages", "promotional": "Marketing or promotional content"}'

# Confidence threshold (0-1) - skip classification if confidence below this
CLASSIFICATION_CONFIDENCE_THRESHOLD=0.6

# OpenAI configuration (required)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.3
```

## Usage

### Automatic Classification (Default)

When emails are fetched via `fetch_and_process_emails`:

```python
from backend.worker.tasks.email_processor import fetch_and_process_emails

# Emails are automatically classified after fetching
task = fetch_and_process_emails.delay(email_account_id, max_results=10)
```

Flow:

1. Fetch emails from Gmail
2. Store as EmailJob records
3. Trigger `classify_email` Celery task for each email
4. Classification results stored in EmailJob

### Manual Classification (Testing)

```bash
# Classify email content directly (no database)
curl -X POST http://localhost:8000/api/v1/email/classify-manual \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "boss@company.com",
    "subject": "Urgent: Q4 Report Due",
    "body": "Please submit the quarterly financial report by EOD today. This is critical for the board meeting."
  }'

# Response:
{
  "email_job_id": "manual",
  "category": "important",
  "confidence": 0.95,
  "explanation": "Urgent business email from senior manager with tight deadline"
}
```

### Programmatic Classification

```python
from backend.llm.classifier import EmailClassifier

classifier = EmailClassifier()

result = classifier.classify(
    sender="boss@company.com",
    subject="Urgent: Q4 Report",
    body="Please submit report by EOD",
)

print(f"Category: {result['category']}")
print(f"Confidence: {result['confidence']:.2%}")
print(f"Explanation: {result['explanation']}")
```

## LLM Behavior

### Prompt Strategy

The classifier sends a structured prompt to OpenAI:

```
You are an email classification assistant. Classify the following email into ONE of these categories:

- important: Time-sensitive or high-priority emails
- actionable: Contains tasks or action items
- followup: Requires a follow-up response
- informational: For reference only
- spam: Unsolicited or unwanted messages
- promotional: Marketing or promotional content

Email Details:
From: {sender}
Subject: {subject}
Body: {body_truncated}

Respond with a JSON object containing:
- "category": The category name (must be one of the listed categories)
- "confidence": A confidence score from 0.0 to 1.0
- "explanation": A brief (one sentence) explanation of why you chose this category

IMPORTANT: Respond ONLY with valid JSON, no other text.
```

### Response Parsing

Response must be valid JSON with three fields:

```json
{
  "category": "important",
  "confidence": 0.95,
  "explanation": "Urgent deadline-driven email from senior manager"
}
```

The classifier:

- Validates category is known (defaults to "informational" if not)
- Clamps confidence to 0.0-1.0
- Truncates explanation to 200 characters
- Stores as integer percentage in database (0-100)

## Error Handling

### Missing Email

```
Response: {"success": false, "error": "EmailJob not found"}
```

### Invalid OpenAI Response

Falls back to safe default:

```python
{
  "category": "informational",
  "confidence": 0.5,
  "explanation": "Classification failed, defaulting to informational"
}
```

### Unknown Category

If LLM returns unknown category, classifier replaces with "informational"

### Low Confidence

If confidence < threshold, classification is still stored but can be filtered out:

```python
emails = db.query(EmailJob).filter(
    EmailJob.classification_confidence >= 80  # 80%+
).all()
```

## Database Queries

### Get all important emails

```python
from backend.models import EmailJob

important_emails = db.query(EmailJob).filter(
    EmailJob.classification == "important"
).all()
```

### Get high-confidence classifications

```python
high_confidence = db.query(EmailJob).filter(
    EmailJob.classification_confidence >= 90  # 90%+
).all()
```

### Get unclassified emails

```python
unclassified = db.query(EmailJob).filter(
    EmailJob.classification.is_(None)
).all()
```

## Performance Considerations

### Token Usage

- Email body truncated to 2000 characters to prevent token overload
- Typical request: ~500 tokens (prompt + response)
- Cost: ~$0.001 per email at gpt-3.5-turbo rates

### Async Processing

Classification happens async via Celery:

- Fetch task completes quickly
- Classification task runs in background
- Results available within seconds typically

### Batch Processing

For bulk classification:

```python
from backend.worker.tasks.classifier import classify_emails_batch

# Classify 100 emails asynchronously
task = classify_emails_batch.apply_async(
    args=([email_id_1, email_id_2, ...],),
)

# Check status
result = task.get()  # Blocks until complete
```

## Testing

### Run Classification Tests

```bash
# All tests
pytest backend/tests/test_email_classification.py -v

# Specific test class
pytest backend/tests/test_email_classification.py::TestEmailClassifierClassification -v

# Specific test
pytest backend/tests/test_email_classification.py::TestEmailClassifierClassification::test_classify_important_email -v
```

### Test Coverage

- **16 tests total** covering:
  - Configuration loading and validation
  - Classification of different email types
  - Error handling (invalid responses, missing emails, unknown categories)
  - Response parsing and validation
  - Celery task integration

### Key Test Scenarios

1. **Important email** - Boss email with deadline
2. **Spam email** - Unsolicited promotional content
3. **Actionable email** - Contains specific task request
4. **Invalid response** - LLM returns non-JSON
5. **Unknown category** - LLM returns category not in config
6. **Low confidence** - Classification below threshold

## Adding Custom Categories

To add new classification categories:

1. Update `.env` EMAIL_CATEGORIES JSON:

```env
EMAIL_CATEGORIES='{"important": "...", "urgent": "Requires immediate action", ...}'
```

2. Restart application to reload config
3. Classifier will use new categories in prompts

Example: Adding "urgent" category

```json
{
  "important": "Time-sensitive or high-priority emails",
  "urgent": "Requires immediate action within hours",
  "actionable": "Contains tasks or action items",
  "followup": "Requires a follow-up response",
  "informational": "For reference only",
  "spam": "Unsolicited or unwanted messages",
  "promotional": "Marketing or promotional content"
}
```

## Limitations & Future Work

### Current Limitations (Phase C Step 1)

- No action execution (auto-reply, archiving, etc.)
- No user preference learning
- No category weighting or custom thresholds per user
- No multi-language support

### Future Enhancements (Phase C Step 2+)

- Auto-reply rule execution
- Email archiving and label operations
- Per-category confidence thresholds
- User feedback to improve classifications
- Batch processing optimization
- Caching of classifier instance
- Custom fine-tuned models per user

## Troubleshooting

### Classification fails with "OpenAI API key not configured"

**Solution**: Set OPENAI_API_KEY in `.env` and restart application

### All emails classified as "informational"

**Check**:

1. Is OPENAI_API_KEY valid?
2. Is API key rate-limited?
3. Check logs for LLM errors

### Confidence always 0.5

**Likely cause**: Invalid LLM response format, check logs for response content

### High latency on email fetching

**Cause**: Classification happening synchronously
**Solution**: Ensure Celery worker is running:

```bash
celery -A backend.worker.celery_app worker -l info
```

## Integration with Other Features

### Email Filtering

```python
# Get important emails only
important = db.query(EmailJob).filter(
    EmailJob.user_id == user_id,
    EmailJob.classification == "important"
).all()
```

### Rule Execution (Future Phase)

Auto-reply rules will use classification:

```python
rule = {
    "name": "Auto-archive promotional",
    "condition": {"category": ["promotional"]},
    "action": {"archive": True}
}
```

### Analytics (Future Phase)

```python
# Category distribution
categories = db.query(
    EmailJob.classification,
    func.count(EmailJob.id)
).group_by(EmailJob.classification).all()
```

## API Reference

### POST /api/v1/email/classify

Classify a single email from database.

**Request**:

```json
{
  "email_job_id": "email-uuid"
}
```

**Response** (202 Accepted):

```json
{
  "task_id": "celery-task-uuid",
  "email_job_id": "email-uuid",
  "status": "submitted"
}
```

### POST /api/v1/email/classify-manual

Classify email content directly.

**Request**:

```json
{
  "sender": "boss@company.com",
  "subject": "Urgent: Q4 Report",
  "body": "Please submit..."
}
```

**Response** (200 OK):

```json
{
  "email_job_id": "manual",
  "category": "important",
  "confidence": 0.95,
  "explanation": "..."
}
```

### GET /api/v1/email/classified

Get classified emails with optional filtering.

**Query Parameters**:

- `category` (optional): Filter by category
- `min_confidence` (optional): Min confidence 0-100
- `limit` (default: 50, max: 100)
- `offset` (default: 0)

**Response** (200 OK):

```json
[
  {
    "id": "email-uuid",
    "subject": "Urgent: Q4 Report",
    "sender": "boss@company.com",
    "classification": "important",
    "classification_confidence": 95,
    "classification_explanation": "...",
    "is_processed": true,
    "created_at": "2024-01-15T10:30:00Z",
    "classified_at": "2024-01-15T10:32:00Z"
  }
]
```

## References

- [LangChain ChatOpenAI](https://python.langchain.com/docs/integrations/chat/openai)
- [OpenAI API Docs](https://platform.openai.com/docs/api-reference)
- [Celery Task Queue](https://docs.celeryproject.org/)
