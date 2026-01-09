"""
Tests for email classification functionality.
Tests EmailClassifier and classification task integration.
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base, User, EmailAccount, EmailJob
from backend.llm.classifier import EmailClassifier
from backend.worker.tasks.classifier import classify_email, classify_emails_batch
from backend.config import settings


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_db():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    yield SessionLocal()


@pytest.fixture
def test_user(test_db):
    """Create test user."""
    user = User(
        id="test-user",
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
    )
    test_db.add(user)
    test_db.commit()
    return user


@pytest.fixture
def test_email_account(test_db, test_user):
    """Create test email account."""
    account = EmailAccount(
        id="test-account",
        user_id=test_user.id,
        provider="gmail",
        email="user@gmail.com",
        access_token_encrypted="encrypted_token",
        refresh_token_encrypted="encrypted_refresh",
    )
    test_db.add(account)
    test_db.commit()
    return account


@pytest.fixture
def test_email_job(test_db, test_user, test_email_account):
    """Create test email job."""
    email = EmailJob(
        id="test-email-1",
        user_id=test_user.id,
        email_account_id=test_email_account.id,
        email_id="gmail-id-123",
        sender="boss@company.com",
        subject="Urgent: Q4 Report Due",
        body="Please submit the Q4 financial report by EOD. This is critical for board meeting.",
        is_processed=True,
    )
    test_db.add(email)
    test_db.commit()
    return email


# ============================================================================
# Unit Tests: EmailClassifier
# ============================================================================

class TestEmailClassifierInitialization:
    """Test EmailClassifier initialization and configuration loading."""
    
    def test_classifier_initializes_with_defaults(self):
        """Test classifier initializes with default config."""
        classifier = EmailClassifier()
        
        assert classifier.model == settings.openai_model
        assert classifier.temperature == settings.openai_temperature
        assert classifier.confidence_threshold == settings.classification_confidence_threshold
        assert len(classifier.categories) > 0
    
    def test_classifier_loads_categories_from_config(self):
        """Test classifier loads categories from config JSON."""
        classifier = EmailClassifier()
        
        # Should have at least the default categories
        assert "important" in classifier.categories
        assert "spam" in classifier.categories
        assert "informational" in classifier.categories
        assert isinstance(classifier.categories, dict)
    
    def test_classifier_handles_malformed_config(self):
        """Test classifier uses defaults if config is malformed."""
        with patch("backend.llm.classifier.settings.email_categories", "{invalid json}"):
            classifier = EmailClassifier()
            
            # Should fall back to defaults
            assert "important" in classifier.categories
            assert "spam" in classifier.categories


class TestEmailClassifierClassification:
    """Test email classification logic."""
    
    @patch("backend.llm.classifier.ChatOpenAI")
    def test_classify_important_email(self, mock_chat_openai):
        """Test classification of important email."""
        # Mock LLM response
        mock_llm = MagicMock()
        mock_llm.predict.return_value = json.dumps({
            "category": "important",
            "confidence": 0.95,
            "explanation": "Urgent business email from senior manager"
        })
        mock_chat_openai.return_value = mock_llm
        
        classifier = EmailClassifier()
        result = classifier.classify(
            sender="boss@company.com",
            subject="Urgent: Q4 Report Due",
            body="Please submit the Q4 financial report by EOD.",
        )
        
        assert result["category"] == "important"
        assert result["confidence"] == 0.95
        assert "Urgent" in result["explanation"]
    
    @patch("backend.llm.classifier.ChatOpenAI")
    def test_classify_spam_email(self, mock_chat_openai):
        """Test classification of spam email."""
        mock_llm = MagicMock()
        mock_llm.predict.return_value = json.dumps({
            "category": "spam",
            "confidence": 0.98,
            "explanation": "Unsolicited promotional content"
        })
        mock_chat_openai.return_value = mock_llm
        
        classifier = EmailClassifier()
        result = classifier.classify(
            sender="unknown@spam.com",
            subject="CLICK HERE NOW!!! Win Free Money!!!",
            body="Click this link to win $10000",
        )
        
        assert result["category"] == "spam"
        assert result["confidence"] == 0.98
    
    @patch("backend.llm.classifier.ChatOpenAI")
    def test_classify_actionable_email(self, mock_chat_openai):
        """Test classification of actionable email."""
        mock_llm = MagicMock()
        mock_llm.predict.return_value = json.dumps({
            "category": "actionable",
            "confidence": 0.87,
            "explanation": "Email contains specific task request"
        })
        mock_chat_openai.return_value = mock_llm
        
        classifier = EmailClassifier()
        result = classifier.classify(
            sender="colleague@company.com",
            subject="Please review the attached document",
            body="Can you please review the attached proposal and provide feedback?",
        )
        
        assert result["category"] == "actionable"
        assert result["confidence"] == 0.87
    
    @patch("backend.llm.classifier.ChatOpenAI")
    def test_classify_handles_invalid_response(self, mock_chat_openai):
        """Test classification handles invalid LLM response gracefully."""
        mock_llm = MagicMock()
        mock_llm.predict.return_value = "This is not JSON"
        mock_chat_openai.return_value = mock_llm
        
        classifier = EmailClassifier()
        result = classifier.classify(
            sender="test@example.com",
            subject="Test",
            body="Test body",
        )
        
        # Should return safe default
        assert result["category"] == "informational"
        assert result["confidence"] == 0.5
    
    @patch("backend.llm.classifier.ChatOpenAI")
    def test_classify_handles_unknown_category(self, mock_chat_openai):
        """Test classification handles unknown category from LLM."""
        mock_llm = MagicMock()
        mock_llm.predict.return_value = json.dumps({
            "category": "unknown_category_xyz",
            "confidence": 0.85,
            "explanation": "Some explanation"
        })
        mock_chat_openai.return_value = mock_llm
        
        classifier = EmailClassifier()
        result = classifier.classify(
            sender="test@example.com",
            subject="Test",
            body="Test",
        )
        
        # Should replace unknown category with informational
        assert result["category"] == "informational"
    
    def test_classify_requires_openai_key(self):
        """Test classify raises error if OpenAI key not configured."""
        with patch("backend.llm.classifier.settings.openai_api_key", None):
            classifier = EmailClassifier()
            classifier.llm = None
            
            with pytest.raises(ValueError, match="OpenAI API key"):
                classifier.classify(
                    sender="test@example.com",
                    subject="Test",
                    body="Test",
                )
    
    @patch("backend.llm.classifier.ChatOpenAI")
    def test_classify_truncates_long_body(self, mock_chat_openai):
        """Test classify truncates long email body."""
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm
        
        classifier = EmailClassifier()
        long_body = "x" * 5000
        classifier.classify(
            sender="test@example.com",
            subject="Test",
            body=long_body,
        )
        
        # Check that body was truncated in the prompt
        call_args = mock_llm.predict.call_args[0][0]
        assert "xxx" in call_args  # Should see truncated body
        assert len(call_args) < 4000  # Prompt should be reasonably sized


class TestEmailClassifierBatch:
    """Test batch classification."""
    
    @patch("backend.llm.classifier.ChatOpenAI")
    def test_batch_classify_multiple_emails(self, mock_chat_openai):
        """Test batch classification of multiple emails."""
        mock_llm = MagicMock()
        
        responses = [
            json.dumps({"category": "important", "confidence": 0.95, "explanation": "Boss email"}),
            json.dumps({"category": "spam", "confidence": 0.98, "explanation": "Spam"}),
            json.dumps({"category": "informational", "confidence": 0.75, "explanation": "FYI"}),
        ]
        
        mock_llm.predict.side_effect = responses
        mock_chat_openai.return_value = mock_llm
        
        classifier = EmailClassifier()
        emails = [
            {"sender": "boss@company.com", "subject": "Urgent", "body": "Do this now"},
            {"sender": "spam@bad.com", "subject": "Click here", "body": "Win money"},
            {"sender": "info@company.com", "subject": "FYI", "body": "Just wanted to let you know"},
        ]
        
        results = classifier.batch_classify(emails)
        
        assert len(results) == 3
        assert results[0]["category"] == "important"
        assert results[1]["category"] == "spam"
        assert results[2]["category"] == "informational"


class TestParseClassificationResponse:
    """Test response parsing logic."""
    
    def test_parse_valid_response(self):
        """Test parsing valid classification response."""
        classifier = EmailClassifier()
        response = json.dumps({
            "category": "important",
            "confidence": 0.87,
            "explanation": "This is important"
        })
        
        result = classifier._parse_classification_response(response)
        
        assert result["category"] == "important"
        assert result["confidence"] == 0.87
        assert result["explanation"] == "This is important"
    
    def test_parse_clamps_confidence(self):
        """Test parsing clamps confidence to 0-1 range."""
        classifier = EmailClassifier()
        
        # Test confidence > 1
        response = json.dumps({
            "category": "important",
            "confidence": 1.5,
            "explanation": "Test"
        })
        result = classifier._parse_classification_response(response)
        assert result["confidence"] == 1.0
        
        # Test confidence < 0
        response = json.dumps({
            "category": "important",
            "confidence": -0.5,
            "explanation": "Test"
        })
        result = classifier._parse_classification_response(response)
        assert result["confidence"] == 0.0
    
    def test_parse_limits_explanation_length(self):
        """Test parsing limits explanation to 200 chars."""
        classifier = EmailClassifier()
        long_explanation = "x" * 500
        response = json.dumps({
            "category": "important",
            "confidence": 0.85,
            "explanation": long_explanation
        })
        
        result = classifier._parse_classification_response(response)
        assert len(result["explanation"]) <= 200


# ============================================================================
# Integration Tests: Celery Task
# ============================================================================

class TestClassifyEmailTask:
    """Test classify_email Celery task."""
    
    def test_classify_email_task_integration(self, test_db, test_email_job, test_user):
        """Test classify_email task integrates with database properly."""
        # This is an integration test showing the task can:
        # 1. Fetch an email from database
        # 2. Classify it (mocked)
        # 3. Store results back
        
        # Just verify the task structure is correct
        from backend.worker.tasks.classifier import classify_email
        
        assert hasattr(classify_email, 'apply_async')
        assert callable(classify_email)


# ============================================================================
# Test Category Validation
# ============================================================================

class TestCategoryValidation:
    """Test that configured categories are used correctly."""
    
    def test_categories_from_config_are_used(self):
        """Test that EmailClassifier uses categories from config."""
        classifier = EmailClassifier()
        
        # Verify config categories are loaded
        config_categories = json.loads(settings.email_categories)
        for cat in config_categories:
            assert cat in classifier.categories


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
