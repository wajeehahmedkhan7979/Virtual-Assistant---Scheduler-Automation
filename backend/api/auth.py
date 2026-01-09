"""
Authentication API endpoints.
Handles user registration, login, and OAuth2 email account linking.
"""
from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
import uuid
import logging

from database import get_db
from models import User, EmailAccount
from security.encryption import (
    hash_password,
    verify_password,
    create_access_token,
    verify_token,
    token_encryption,
)
from connectors.gmail import GmailConnector
from config import settings

logger = logging.getLogger(__name__)

# Router for auth endpoints
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================================
# Request/Response Models
# ============================================================================


class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: str = Field(None, description="User's full name")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "john_doe",
                "password": "secure_password_123",
                "full_name": "John Doe",
            }
        }


class UserLoginRequest(BaseModel):
    """User login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "secure_password_123",
            }
        }


class TokenResponse(BaseModel):
    """OAuth2-compatible token response."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
            }
        }


class UserResponse(BaseModel):
    """User response model."""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    username: str = Field(..., description="User username")
    full_name: str = Field(None, description="User full name")
    is_active: bool = Field(default=True, description="Account active status")
    created_at: str = Field(..., description="Account creation timestamp")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "username": "john_doe",
                "full_name": "John Doe",
                "is_active": True,
                "created_at": "2024-01-01T12:00:00",
            }
        }


# ============================================================================
# Endpoint: Register
# ============================================================================


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: Session = Depends(get_db),
):
    """
    Register a new user account.
    
    - **email**: Valid email address (must be unique)
    - **username**: Unique username (3-50 characters)
    - **password**: Password (minimum 8 characters)
    - **full_name**: Optional full name
    
    Returns: New user object with authentication details
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email address already registered",
        )

    # Check if username already exists
    existing_username = db.query(User).filter(User.username == request.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    # Create new user
    hashed_password = hash_password(request.password)
    new_user = User(
        email=request.email,
        username=request.username,
        hashed_password=hashed_password,
        full_name=request.full_name,
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ============================================================================
# Endpoint: Login
# ============================================================================


@router.post("/login", response_model=TokenResponse)
async def login(
    request: UserLoginRequest,
    db: Session = Depends(get_db),
):
    """
    User login endpoint.
    
    Returns JWT access token valid for 24 hours.
    
    - **email**: Registered email address
    - **password**: Account password
    
    Returns: Access token with expiration
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Create access token
    expires_delta = timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": user.id, "email": user.email},
        expires_delta=expires_delta,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=int(expires_delta.total_seconds()),
    )


# ============================================================================
# Endpoint: Get Current User
# ============================================================================


def get_current_user(
    authorization: str = None,
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    
    Accepts token in Authorization header: "Bearer <token>"
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not authorization:
        raise credentials_exception
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise credentials_exception
    
    token = parts[1]
    
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Get current authenticated user information.
    
    Requires: Valid JWT token in Authorization header
    
    Returns: Current user object
    """
    return current_user

# ============================================================================
# OAuth2 Email Accounts: Gmail
# ============================================================================


class GmailAuthStartRequest(BaseModel):
    """Request to start Gmail OAuth2 flow."""
    pass


class GmailAuthStartResponse(BaseModel):
    """OAuth2 authorization URL."""
    authorization_url: str = Field(..., description="URL to redirect user to Gmail authorization")


@router.post("/gmail/authorize", response_model=GmailAuthStartResponse)
async def start_gmail_oauth(
    request: GmailAuthStartRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Start Gmail OAuth2 flow.
    
    Returns authorization URL for user to visit. After user approves,
    they will be redirected to /auth/gmail/callback with authorization code.
    
    Requires: Valid JWT token in Authorization header
    
    Returns: Authorization URL
    """
    # Generate state parameter for CSRF protection
    state = str(uuid.uuid4())
    
    # Create Gmail connector
    gmail = GmailConnector(
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
        redirect_uri=settings.gmail_redirect_uri,
    )
    
    # Get authorization URL
    auth_url = gmail.get_authorization_url(state=state)
    
    logger.info(f"Started Gmail OAuth flow for user {current_user.id}")
    
    return GmailAuthStartResponse(authorization_url=auth_url)


@router.get("/gmail/callback")
async def gmail_oauth_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    """
    Handle Gmail OAuth2 callback.
    
    This endpoint is called by Google after user authorizes our app.
    Exchanges authorization code for access/refresh tokens and stores them
    encrypted in the database.
    
    Query Parameters:
    - code: Authorization code from Google
    - state: State parameter for CSRF validation
    
    Returns: Success/error message
    """
    try:
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing authorization code",
            )
        
        # Create Gmail connector
        gmail = GmailConnector(
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
            redirect_uri=settings.gmail_redirect_uri,
        )
        
        # Exchange code for tokens
        token_data = gmail.handle_oauth_callback(code=code, state=state)
        
        # Extract email from JWT token in authorization_code
        # For now, we'll fetch it from Gmail API using the access token
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials as GoogleCredentials
        
        service = build(
            "gmail",
            "v1",
            credentials=GoogleCredentials(token=token_data["access_token"]),
        )
        profile = service.users().getProfile(userId="me").execute()
        gmail_email = profile.get("emailAddress")
        
        # For this callback, we can't directly get the user because
        # we don't have their JWT. In a real app, you'd:
        # 1. Store the code in session
        # 2. Redirect to a frontend page that has the JWT
        # 3. Have frontend POST to a protected endpoint to link the account
        
        # For MVP, return instructions
        logger.info(f"Gmail OAuth callback received for {gmail_email}")
        
        return {
            "status": "success",
            "message": "Gmail account authorized. To complete linking, make a POST request to /auth/gmail/link with your JWT token and this data.",
            "gmail_email": gmail_email,
            "access_token": token_data["access_token"],
            "refresh_token": token_data["refresh_token"],
            "expires_at": token_data["expires_at"],
        }
        
    except Exception as e:
        logger.error(f"Gmail OAuth callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth callback failed: {str(e)}",
        )


class GmailLinkRequest(BaseModel):
    """Request to link Gmail account to user."""
    access_token: str = Field(..., description="Gmail access token from OAuth callback")
    refresh_token: str = Field(..., description="Gmail refresh token from OAuth callback")
    gmail_email: str = Field(..., description="Gmail email address")
    expires_at: str = Field(..., description="Token expiration timestamp")


@router.post("/gmail/link", response_model=dict)
async def link_gmail_account(
    request: GmailLinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Link Gmail account to current user.
    
    Stores encrypted access/refresh tokens in EmailAccount table.
    
    Requires: Valid JWT token and Gmail OAuth tokens from callback
    
    Returns: Email account details
    """
    try:
        # Check if this Gmail account is already linked to another user
        existing = db.query(EmailAccount).filter(
            EmailAccount.provider == "gmail",
            EmailAccount.email == request.gmail_email,
        ).first()
        
        if existing and existing.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Gmail account already linked to another user",
            )
        
        # Encrypt tokens before storing
        access_token_encrypted = token_encryption.encrypt(request.access_token)
        refresh_token_encrypted = token_encryption.encrypt(request.refresh_token) if request.refresh_token else None
        
        # Create or update EmailAccount
        if existing:
            existing.access_token_encrypted = access_token_encrypted
            existing.refresh_token_encrypted = refresh_token_encrypted
            existing.token_expires_at = datetime.fromisoformat(request.expires_at.replace('Z', '+00:00'))
            existing.is_active = True
            db.commit()
            db.refresh(existing)
            email_account = existing
            logger.info(f"Updated Gmail account {request.gmail_email} for user {current_user.id}")
        else:
            email_account = EmailAccount(
                user_id=current_user.id,
                provider="gmail",
                email=request.gmail_email,
                access_token_encrypted=access_token_encrypted,
                refresh_token_encrypted=refresh_token_encrypted,
                token_expires_at=datetime.fromisoformat(request.expires_at.replace('Z', '+00:00')),
                is_active=True,
            )
            db.add(email_account)
            db.commit()
            db.refresh(email_account)
            logger.info(f"Linked Gmail account {request.gmail_email} to user {current_user.id}")
        
        return {
            "status": "success",
            "message": f"Gmail account {request.gmail_email} linked successfully",
            "email_account_id": email_account.id,
            "provider": email_account.provider,
            "email": email_account.email,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error linking Gmail account: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link Gmail account: {str(e)}",
        )