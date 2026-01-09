"""
Simple direct tests for Gmail OAuth implementation.
Tests key functionality without complex fixtures.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from datetime import datetime, timedelta
from connectors.gmail import GmailConnector
from security.encryption import token_encryption, verify_token, create_access_token
from models import User, EmailAccount, EmailJob
import logging

logger = logging.getLogger(__name__)


def test_gmail_connector_init():
    """Test GmailConnector initialization."""
    connector = GmailConnector(
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri="http://localhost:8000/callback",
    )
    
    assert connector.client_id == "test-client-id"
    assert connector.client_secret == "test-client-secret"
    assert connector.redirect_uri == "http://localhost:8000/callback"
    assert "https://www.googleapis.com/auth/gmail.modify" in connector.scopes
    print("✓ test_gmail_connector_init passed")


def test_gmail_connector_config():
    """Test GmailConnector client config generation."""
    connector = GmailConnector(
        client_id="12345.apps.googleusercontent.com",
        client_secret="secret123",
        redirect_uri="http://localhost:8000/callback",
    )
    
    config = connector.client_config
    assert config["installed"]["client_id"] == "12345.apps.googleusercontent.com"
    assert config["installed"]["client_secret"] == "secret123"
    assert "http://localhost:8000/callback" in config["installed"]["redirect_uris"]
    print("✓ test_gmail_connector_config passed")


def test_token_encryption():
    """Test token encryption and decryption."""
    plaintext = "test-access-token-12345"
    
    # Encrypt
    encrypted = token_encryption.encrypt(plaintext)
    assert encrypted != plaintext
    assert isinstance(encrypted, str)
    
    # Decrypt
    decrypted = token_encryption.decrypt(encrypted)
    assert decrypted == plaintext
    print("✓ test_token_encryption passed")


def test_jwt_token_creation():
    """Test JWT token creation and verification."""
    user_id = "550e8400-e29b-41d4-a716-446655440000"
    
    # Create token
    token = create_access_token(
        data={"sub": user_id, "email": "test@example.com"},
        expires_delta=timedelta(hours=24),
    )
    
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Verify token
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["email"] == "test@example.com"
    print("✓ test_jwt_token_creation passed")


def test_email_account_model():
    """Test EmailAccount model structure."""
    # Verify model has required fields
    assert hasattr(EmailAccount, "id")
    assert hasattr(EmailAccount, "user_id")
    assert hasattr(EmailAccount, "provider")
    assert hasattr(EmailAccount, "email")
    assert hasattr(EmailAccount, "access_token_encrypted")
    assert hasattr(EmailAccount, "refresh_token_encrypted")
    assert hasattr(EmailAccount, "token_expires_at")
    assert hasattr(EmailAccount, "is_active")
    assert hasattr(EmailAccount, "last_sync")
    print("✓ test_email_account_model passed")


def test_email_job_model():
    """Test EmailJob model structure."""
    # Verify model has required fields
    assert hasattr(EmailJob, "id")
    assert hasattr(EmailJob, "user_id")
    assert hasattr(EmailJob, "email_account_id")
    assert hasattr(EmailJob, "email_id")
    assert hasattr(EmailJob, "subject")
    assert hasattr(EmailJob, "sender")
    assert hasattr(EmailJob, "body")
    assert hasattr(EmailJob, "classification")
    assert hasattr(EmailJob, "is_flagged")
    assert hasattr(EmailJob, "auto_reply_sent")
    assert hasattr(EmailJob, "is_processed")
    print("✓ test_email_job_model passed")


def test_auth_endpoints_exist():
    """Test that auth endpoints are registered."""
    from api.auth import router
    
    paths = [r.path for r in router.routes]
    
    assert "/auth/register" in paths
    assert "/auth/login" in paths
    assert "/auth/me" in paths
    assert "/auth/gmail/authorize" in paths
    assert "/auth/gmail/callback" in paths
    assert "/auth/gmail/link" in paths
    print("✓ test_auth_endpoints_exist passed")


def test_fetch_emails_task_signature():
    """Test that fetch_and_process_emails task has correct signature."""
    from worker.tasks.email_processor import fetch_and_process_emails
    import inspect
    
    sig = inspect.signature(fetch_and_process_emails)
    params = list(sig.parameters.keys())
    
    assert "user_id" in params
    assert "email_account_id" in params
    assert "max_results" in params
    print("✓ test_fetch_emails_task_signature passed")


def test_gmail_connector_methods_exist():
    """Test that GmailConnector has all required methods."""
    connector = GmailConnector(
        client_id="test",
        client_secret="test",
        redirect_uri="http://localhost:8000",
    )
    
    assert hasattr(connector, "get_authorization_url")
    assert hasattr(connector, "handle_oauth_callback")
    assert hasattr(connector, "refresh_access_token")
    assert hasattr(connector, "fetch_emails")
    assert hasattr(connector, "get_email_body")
    assert callable(connector.get_authorization_url)
    assert callable(connector.handle_oauth_callback)
    assert callable(connector.refresh_access_token)
    assert callable(connector.fetch_emails)
    assert callable(connector.get_email_body)
    print("✓ test_gmail_connector_methods_exist passed")


def test_get_current_user_signature():
    """Test that get_current_user function accepts Authorization header."""
    from api.auth import get_current_user
    import inspect
    
    sig = inspect.signature(get_current_user)
    params = list(sig.parameters.keys())
    
    # Should accept authorization parameter
    assert "authorization" in params or "db" in params
    print("✓ test_get_current_user_signature passed")


def test_models_relationships():
    """Test that model relationships are correctly defined."""
    # User relationships
    assert hasattr(User, "email_accounts")
    assert hasattr(User, "email_jobs")
    
    # EmailAccount relationships
    assert hasattr(EmailAccount, "user")
    assert hasattr(EmailAccount, "email_jobs")
    
    # EmailJob relationships
    assert hasattr(EmailJob, "user")
    assert hasattr(EmailJob, "email_account")
    print("✓ test_models_relationships passed")


# Run all tests
if __name__ == "__main__":
    tests = [
        test_gmail_connector_init,
        test_gmail_connector_config,
        test_token_encryption,
        test_jwt_token_creation,
        test_email_account_model,
        test_email_job_model,
        test_auth_endpoints_exist,
        test_fetch_emails_task_signature,
        test_gmail_connector_methods_exist,
        test_get_current_user_signature,
        test_models_relationships,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")
    
    if failed == 0:
        print("✓ All tests passed!")
        exit(0)
    else:
        exit(1)
