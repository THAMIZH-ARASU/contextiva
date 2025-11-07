"""Authentication routes for JWT token generation."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.domain.models.user import IUserRepository
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.shared.config.settings import load_settings
from src.shared.infrastructure.database.connection import init_pool
from src.shared.utils.security import create_access_token, verify_password


router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_user_repository() -> IUserRepository:
    """Dependency to get the user repository instance."""
    pool = await init_pool()
    return UserRepository(pool)


@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo: IUserRepository = Depends(get_user_repository),
) -> dict[str, str]:
    """
    OAuth2 compatible token login endpoint.
    
    Args:
        form_data: The OAuth2 password request form with username and password
        user_repo: The user repository dependency
        
    Returns:
        A dictionary containing the access token and token type
        
    Raises:
        HTTPException: 401 if credentials are invalid
    """
    # Retrieve user by username
    user = await user_repo.get_by_username(form_data.username)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    settings = load_settings()
    access_token_expires = timedelta(minutes=settings.security.jwt_expires_minutes)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
