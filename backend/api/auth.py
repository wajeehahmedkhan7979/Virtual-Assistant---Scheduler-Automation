"""
Authentication API endpoints.
Handles user registration, login, and token management.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from database import get_db
from models import User
from security.encryption import (
    hash_password,
    verify_password,
    create_access_token,
)

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
    token: str,
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    """
    from security.encryption import verify_token

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

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
