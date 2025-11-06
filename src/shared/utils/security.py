"""Security utilities for JWT token handling and password hashing."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.shared.config.settings import load_settings


# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Load settings
settings = load_settings()


def get_password_hash(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    
    Args:
        password: The plaintext password to hash
        
    Returns:
        The hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a hashed password.
    
    Args:
        plain_password: The plaintext password to verify
        hashed_password: The hashed password to compare against
        
    Returns:
        True if the password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: The data to encode in the token (typically {"sub": username})
        expires_delta: Optional custom expiration time
        
    Returns:
        The encoded JWT token as a string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.security.jwt_expires_minutes)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.security.jwt_secret,
        algorithm=settings.security.jwt_algorithm
    )
    
    return encoded_jwt


def verify_token(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        The decoded token payload
        
    Raises:
        JWTError: If the token is invalid or expired
    """
    payload = jwt.decode(
        token,
        settings.security.jwt_secret,
        algorithms=[settings.security.jwt_algorithm]
    )
    return payload
