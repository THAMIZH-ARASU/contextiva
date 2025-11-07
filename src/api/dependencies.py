"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from typing import Callable, List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from src.domain.models.user import IUserRepository, User
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.shared.infrastructure.database.connection import init_pool
from src.shared.utils.security import verify_token


# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_user_repository() -> IUserRepository:
    """
    Dependency to get the user repository instance.
    """
    pool = await init_pool()
    return UserRepository(pool)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: IUserRepository = Depends(get_user_repository),
) -> User:
    """
    Get the current authenticated user from the JWT token.
    
    Args:
        token: The JWT token from the Authorization header
        user_repo: The user repository dependency
        
    Returns:
        The authenticated User entity
        
    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode and verify the token
        payload = verify_token(token)
        username: str | None = payload.get("sub")
        
        if username is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Retrieve the user from the repository
    user = await user_repo.get_by_username(username)
    
    if user is None:
        raise credentials_exception
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def require_role(required_roles: List[str]) -> Callable:
    """
    Dependency factory for role-based access control (RBAC).
    
    NOTE: This is a stub implementation. Complex RBAC logic including
    hierarchical roles and resource-level permissions is deferred to
    future stories.
    
    Args:
        required_roles: List of roles, user must have at least one
        
    Returns:
        A dependency function that validates user roles
        
    Example:
        @router.get("/admin", dependencies=[Depends(require_role(["admin"]))])
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        """
        Check if the current user has at least one of the required roles.
        
        Args:
            current_user: The authenticated user
            
        Returns:
            The user if authorized
            
        Raises:
            HTTPException: 403 if user lacks required role
        """
        # Check if user has any of the required roles
        user_has_role = any(role in current_user.roles for role in required_roles)
        
        if not user_has_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        
        return current_user
    
    return role_checker
