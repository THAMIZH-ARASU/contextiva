"""UserRepository implementation using asyncpg."""

from __future__ import annotations

from typing import Iterable, Optional
from uuid import UUID

import asyncpg

from src.domain.models.user import IUserRepository, User
from src.shared.utils.errors import UserNotFoundError


class UserRepository(IUserRepository):
    """Concrete implementation of IUserRepository using asyncpg."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        """
        Initialize the repository with a database connection pool.
        
        Args:
            pool: The asyncpg connection pool
        """
        self.pool = pool

    async def create(self, user: User) -> User:
        """
        Create a new user in the database.
        
        Args:
            user: The User entity to create
            
        Returns:
            The created User entity
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (id, username, email, hashed_password, is_active, roles, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, now(), now())
                """,
                user.id,
                user.username,
                user.email,
                user.hashed_password,
                user.is_active,
                user.roles,
            )
        return user

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """
        Retrieve a user by ID.
        
        Args:
            user_id: The UUID of the user
            
        Returns:
            The User entity if found, None otherwise
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, username, email, hashed_password, is_active, roles
                FROM users
                WHERE id = $1
                """,
                user_id,
            )
        
        if not row:
            return None
        
        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            hashed_password=row["hashed_password"],
            is_active=row["is_active"],
            roles=list(row["roles"]) if row["roles"] else [],
        )

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Retrieve a user by username.
        
        Args:
            username: The username to search for
            
        Returns:
            The User entity if found, None otherwise
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, username, email, hashed_password, is_active, roles
                FROM users
                WHERE username = $1
                """,
                username,
            )
        
        if not row:
            return None
        
        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            hashed_password=row["hashed_password"],
            is_active=row["is_active"],
            roles=list(row["roles"]) if row["roles"] else [],
        )

    async def get_all(self, limit: int = 100, offset: int = 0) -> Iterable[User]:
        """
        Retrieve all users with pagination.
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            An iterable of User entities
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, username, email, hashed_password, is_active, roles
                FROM users
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        
        return [
            User(
                id=row["id"],
                username=row["username"],
                email=row["email"],
                hashed_password=row["hashed_password"],
                is_active=row["is_active"],
                roles=list(row["roles"]) if row["roles"] else [],
            )
            for row in rows
        ]

    async def update(self, user: User) -> User:
        """
        Update an existing user.
        
        Args:
            user: The User entity with updated data
            
        Returns:
            The updated User entity
            
        Raises:
            UserNotFoundError: If the user does not exist
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE users
                SET username = $2, email = $3, hashed_password = $4, is_active = $5, roles = $6, updated_at = now()
                WHERE id = $1
                """,
                user.id,
                user.username,
                user.email,
                user.hashed_password,
                user.is_active,
                user.roles,
            )
        
        if result != "UPDATE 1":
            raise UserNotFoundError(f"User with id {user.id} not found")
        
        return user

    async def delete(self, user_id: UUID) -> None:
        """
        Delete a user by ID.
        
        Args:
            user_id: The UUID of the user to delete
            
        Raises:
            UserNotFoundError: If the user does not exist
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM users
                WHERE id = $1
                """,
                user_id,
            )
        
        if result != "DELETE 1":
            raise UserNotFoundError(f"User with id {user_id} not found")
