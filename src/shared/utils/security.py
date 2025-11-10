"""Security utilities for JWT token handling and password hashing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from jose import JWTError, jwt

from src.shared.config.settings import load_settings

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
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a hashed password.
    
    Args:
        plain_password: The plaintext password to verify
        hashed_password: The hashed password to compare against
        
    Returns:
        True if the password matches, False otherwise
    """
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_bytes)


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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.security.jwt_expires_minutes)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    })
    
    encoded_jwt: str = jwt.encode(
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
    payload: Dict[str, Any] = jwt.decode(
        token,
        settings.security.jwt_secret,
        algorithms=[settings.security.jwt_algorithm]
    )
    return payload
