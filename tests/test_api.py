"""
Test API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint():
    """Test API root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


# Placeholder tests for endpoints to be implemented in Phase B
# - test_register_user()
# - test_login_user()
# - test_gmail_oauth_flow()
# - test_fetch_emails()
# - test_create_auto_reply_rule()
# - test_trigger_data_analysis()
