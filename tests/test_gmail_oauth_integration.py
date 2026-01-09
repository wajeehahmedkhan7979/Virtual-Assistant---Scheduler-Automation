"""
Integration tests for Gmail OAuth2 and email ingestion.

Tests the complete flow:
1. User registration
2. Gmail OAuth authorization URL generation
3. Email account linking
4. Email fetching and storage
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json

from main import app
from database import get_db, SessionLocal
from models import Base, User, EmailAccount, EmailJob


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_user_email():
    """Test user email."""
    return "testuser@example.com"


@pytest.fixture
def test_user_password():
    """Test user password."""
    return "TestPassword123"


@pytest.fixture
def test_gmail_email():
    """Test Gmail email."""
    return "testuser@gmail.com"


@pytest.fixture
def test_access_token():
    """Mock access token."""
    return "ya29.test_access_token_12345"


@pytest.fixture
def test_refresh_token():
    """Mock refresh token."""
    return "1//test_refresh_token_12345"


# ============================================================================
# Test: User Registration
# ============================================================================


def test_user_registration(client, test_user_email, test_user_password):
    """Test user registration endpoint."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user_email,
            "username": "testuser",
            "password": test_user_password,
            "full_name": "Test User",
        },
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user_email
    assert data["username"] == "testuser"
    assert data["full_name"] == "Test User"
    assert "id" in data


def test_user_login(client, test_user_email, test_user_password):
    """Test user login endpoint."""
    # Register user first
    client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user_email,
            "username": "testuser",
            "password": test_user_password,
            "full_name": "Test User",
        },
    )
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_email,
            "password": test_user_password,
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert "expires_in" in data


# ============================================================================
# Test: Gmail OAuth Flow
# ============================================================================


@patch("connectors.gmail.GmailConnector.get_authorization_url")
def test_start_gmail_oauth(
    mock_get_auth_url,
    client,
    test_user_email,
    test_user_password,
):
    """Test starting Gmail OAuth flow."""
    # Register and login user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user_email,
            "username": "testuser",
            "password": test_user_password,
            "full_name": "Test User",
        },
    )
    
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_email,
            "password": test_user_password,
        },
    )
    access_token = login_response.json()["access_token"]
    
    # Mock Gmail OAuth URL
    mock_auth_url = "https://accounts.google.com/o/oauth2/auth?client_id=test&state=abc123"
    mock_get_auth_url.return_value = mock_auth_url
    
    # Request OAuth authorization URL
    response = client.post(
        "/api/v1/auth/gmail/authorize",
        json={},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "authorization_url" in data
    assert "accounts.google.com" in data["authorization_url"]


# ============================================================================
# Test: Link Gmail Account
# ============================================================================


def test_link_gmail_account(
    client,
    test_user_email,
    test_user_password,
    test_gmail_email,
    test_access_token,
    test_refresh_token,
):
    """Test linking Gmail account to user."""
    # Register and login user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user_email,
            "username": "testuser",
            "password": test_user_password,
            "full_name": "Test User",
        },
    )
    
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_email,
            "password": test_user_password,
        },
    )
    access_token = login_response.json()["access_token"]
    
    # Link Gmail account
    expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    response = client.post(
        "/api/v1/auth/gmail/link",
        json={
            "access_token": test_access_token,
            "refresh_token": test_refresh_token,
            "gmail_email": test_gmail_email,
            "expires_at": expires_at,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "email_account_id" in data
    assert data["provider"] == "gmail"
    assert data["email"] == test_gmail_email


# ============================================================================
# Test: Email Fetching and Storage
# ============================================================================


@patch("worker.tasks.email_processor.GmailConnector.fetch_emails")
def test_fetch_and_process_emails_task(
    mock_fetch_emails,
    test_user_email,
    test_user_password,
    test_gmail_email,
    test_access_token,
    test_refresh_token,
):
    """Test fetch_and_process_emails Celery task."""
    from worker.tasks.email_processor import fetch_and_process_emails
    
    # Setup database
    db = SessionLocal()
    
    # Create test user
    from security.encryption import hash_password, token_encryption
    user = User(
        email=test_user_email,
        username="testuser",
        hashed_password=hash_password(test_user_password),
        full_name="Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create test email account
    email_account = EmailAccount(
        user_id=user.id,
        provider="gmail",
        email=test_gmail_email,
        access_token_encrypted=token_encryption.encrypt(test_access_token),
        refresh_token_encrypted=token_encryption.encrypt(test_refresh_token),
        token_expires_at=datetime.utcnow() + timedelta(hours=1),
        is_active=True,
    )
    db.add(email_account)
    db.commit()
    db.refresh(email_account)
    
    # Mock Gmail API response
    mock_fetch_emails.return_value = [
        {
            "message_id": "msg_001",
            "thread_id": "thread_001",
            "subject": "Test Email 1",
            "from": "sender1@example.com",
            "to": test_gmail_email,
            "cc": "",
            "date": "2024-01-01T12:00:00",
            "body": "This is the first test email.",
            "labels": ["UNREAD"],
            "is_unread": True,
        },
        {
            "message_id": "msg_002",
            "thread_id": "thread_002",
            "subject": "Test Email 2",
            "from": "sender2@example.com",
            "to": test_gmail_email,
            "cc": "",
            "date": "2024-01-02T12:00:00",
            "body": "This is the second test email.",
            "labels": ["UNREAD"],
            "is_unread": True,
        },
    ]
    
    # Call task
    result = fetch_and_process_emails(user_id=user.id, email_account_id=email_account.id)
    
    # Verify result
    assert result["status"] == "success"
    assert result["emails_fetched"] == 2
    assert result["emails_processed"] == 2
    assert len(result["errors"]) == 0
    
    # Verify emails stored in database
    email_jobs = db.query(EmailJob).filter(
        EmailJob.user_id == user.id,
        EmailJob.email_account_id == email_account.id,
    ).all()
    
    assert len(email_jobs) == 2
    assert email_jobs[0].subject == "Test Email 1"
    assert email_jobs[0].sender == "sender1@example.com"
    assert email_jobs[0].is_processed == False
    
    assert email_jobs[1].subject == "Test Email 2"
    assert email_jobs[1].sender == "sender2@example.com"
    
    # Verify last_sync was updated
    db.refresh(email_account)
    assert email_account.last_sync is not None
    
    db.close()


# ============================================================================
# Test: End-to-End Email Ingestion
# ============================================================================


@patch("worker.tasks.email_processor.GmailConnector.fetch_emails")
def test_end_to_end_email_ingestion(
    mock_fetch_emails,
    client,
    test_user_email,
    test_user_password,
    test_gmail_email,
    test_access_token,
    test_refresh_token,
):
    """
    Test complete email ingestion flow:
    1. Register user
    2. Login
    3. Link Gmail account
    4. Fetch emails
    5. Verify emails stored
    """
    # Step 1: Register user
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user_email,
            "username": "testuser",
            "password": test_user_password,
            "full_name": "Test User",
        },
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]
    
    # Step 2: Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_email,
            "password": test_user_password,
        },
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    
    # Step 3: Link Gmail account
    expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    link_response = client.post(
        "/api/v1/auth/gmail/link",
        json={
            "access_token": test_access_token,
            "refresh_token": test_refresh_token,
            "gmail_email": test_gmail_email,
            "expires_at": expires_at,
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert link_response.status_code == 200
    email_account_id = link_response.json()["email_account_id"]
    
    # Step 4: Mock Gmail API and fetch emails
    mock_fetch_emails.return_value = [
        {
            "message_id": "msg_123",
            "thread_id": "thread_123",
            "subject": "Important Update",
            "from": "boss@company.com",
            "to": test_gmail_email,
            "cc": "",
            "date": "2024-01-01T10:00:00",
            "body": "Your project report is due tomorrow.",
            "labels": ["UNREAD"],
            "is_unread": True,
        },
    ]
    
    # Import task and run
    from worker.tasks.email_processor import fetch_and_process_emails
    
    result = fetch_and_process_emails(user_id=user_id, email_account_id=email_account_id)
    
    # Step 5: Verify result
    assert result["status"] == "success"
    assert result["emails_fetched"] == 1
    assert result["emails_processed"] == 1
    
    # Verify emails in database
    db = SessionLocal()
    email_jobs = db.query(EmailJob).filter(
        EmailJob.user_id == user_id,
        EmailJob.email_account_id == email_account_id,
    ).all()
    
    assert len(email_jobs) == 1
    assert email_jobs[0].subject == "Important Update"
    assert email_jobs[0].sender == "boss@company.com"
    assert email_jobs[0].body == "Your project report is due tomorrow."
    
    db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
