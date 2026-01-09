"""
Basic unit tests for models and database.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, User, EmailAccount
from security.encryption import TokenEncryption

# Test database setup
@pytest.fixture(scope="session")
def test_db():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def test_user_creation(test_db):
    """Test creating a user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
        full_name="Test User",
    )
    test_db.add(user)
    test_db.commit()
    
    assert user.id is not None
    assert user.email == "test@example.com"


def test_email_account_creation(test_db):
    """Test creating an email account."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
    )
    test_db.add(user)
    test_db.commit()
    
    email_account = EmailAccount(
        user_id=user.id,
        provider="gmail",
        email="test@gmail.com",
        access_token_encrypted="encrypted_token",
    )
    test_db.add(email_account)
    test_db.commit()
    
    assert email_account.id is not None
    assert email_account.provider == "gmail"


def test_token_encryption():
    """Test token encryption/decryption."""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key()
    encryption = TokenEncryption(key=key.decode())
    
    plaintext = "my-secret-token"
    encrypted = encryption.encrypt(plaintext)
    decrypted = encryption.decrypt(encrypted)
    
    assert decrypted == plaintext
