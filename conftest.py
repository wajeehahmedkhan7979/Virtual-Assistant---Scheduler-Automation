"""
Pytest configuration and fixtures.
"""
import os
import sys

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

import pytest

try:
    from fastapi.testclient import TestClient

    @pytest.fixture(scope="session")
    def client():
        """Test client for FastAPI app."""
        from main import app
        return TestClient(app)
except ImportError:
    pass
