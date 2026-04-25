"""
API v1 authentication endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import jwt
import hashlib
import secrets

from app.core.database import get_db
from app.models import User
from app.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse,
    ErrorResponse
)
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])


# ============================================================================
# Helper Functions
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> tuple:
    """
    Create JWT access token.
    
    Returns: (token, expiration_seconds)
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=24)
    
    expire = datetime.utcnow() + expires_delta
    payload = {
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    
    return token, int(expires_delta.total_seconds())


def verify_token(token: str) -> Optional[int]:
    """
    Verify JWT token and return user_id.
    
    Returns: user_id if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None
        return user_id
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ============================================================================
# Authentication Routes
# ============================================================================

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Register a new user.
    
    **Parameters:**
    - email: User email address (must be unique)
    - username: Username (3-50 characters, must be unique)
    - password: Password (minimum 8 characters)
    - full_name: Optional full name
    - timezone: User timezone (default: UTC)
    
    **Returns:** Newly created user object
    """
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) |
        (User.username == user_data.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered"
        )
    
    # Create new user
    password_hash = hash_password(user_data.password)
    api_key = secrets.token_urlsafe(32)
    
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        password_hash=password_hash,
        full_name=user_data.full_name,
        timezone=user_data.timezone,
        api_key=api_key,
        plan="FREE",
        is_active=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse.from_orm(new_user)


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    User login.
    
    **Parameters:**
    - email: User email address
    - password: User password
    
    **Returns:** Access token and user information
    """
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    password_hash = hash_password(credentials.password)
    if user.password_hash != password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    
    # Create access token
    token, expires_in = create_access_token(user.id)
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user_id=user.id
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    current_token: str,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Refresh authentication token.
    
    **Parameters:**
    - current_token: Current access token (in Authorization header)
    
    **Returns:** New access token
    """
    user_id = verify_token(current_token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    # Verify user exists and is active
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Create new token
    token, expires_in = create_access_token(user.id)
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
        user_id=user.id
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str,
    db: Session = Depends(get_db)
) -> UserResponse:
    """
    Get current user profile.
    
    **Authorization:** Required (pass token in Authorization header)
    
    **Returns:** Current user's profile information
    """
    user_id = verify_token(token)
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.post("/logout")
async def logout():
    """
    Logout user (for frontend to clear token).
    
    Note: JWT tokens are stateless. Use token expiration for security.
    This endpoint is mainly for frontend to signal logout.
    """
    return {"message": "Successfully logged out. Please discard your token."}
