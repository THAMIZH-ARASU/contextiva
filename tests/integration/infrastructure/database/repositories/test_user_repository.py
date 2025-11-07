"""Integration tests for UserRepository."""

from uuid import uuid4

import pytest
import asyncpg

from src.domain.models.user import User
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.shared.config.settings import load_settings
from src.shared.utils.errors import UserNotFoundError


async def get_fresh_pool():
    """Create a fresh connection pool for each test (bypass singleton)."""
    settings = load_settings()
    return await asyncpg.create_pool(dsn=settings.db.dsn, min_size=1, max_size=5)


class TestUserRepositoryCreate:
    """Tests for UserRepository.create()."""

    @pytest.mark.asyncio
    async def test_create_user_successfully(self):
        """Test creating a new user successfully."""
        # Arrange
        pool = await get_fresh_pool()
        user_repo = UserRepository(pool)
        
        user = User(
            username="testuser1",
            email="testuser1@example.com",
            hashed_password="$2b$12$hashedpassword",
            roles=["user"],
        )

        try:
            # Act
            created_user = await user_repo.create(user)

            # Assert
            assert created_user.id == user.id
            assert created_user.username == user.username
            assert created_user.email == user.email
        finally:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM users WHERE username LIKE 'test%'")
            await pool.close()

    @pytest.mark.asyncio
    async def test_create_user_with_duplicate_username_fails(self):
        """Test that creating user with duplicate username fails."""
        # Arrange
        pool = await get_fresh_pool()
        user_repo = UserRepository(pool)
        
        user1 = User(
            username="testuser2",
            email="testuser2a@example.com",
            hashed_password="$2b$12$hashedpassword",
        )
        user2 = User(
            username="testuser2",  # Same username
            email="testuser2b@example.com",  # Different email
            hashed_password="$2b$12$hashedpassword",
        )

        try:
            # Act
            await user_repo.create(user1)

            # Assert - should raise exception for duplicate username
            with pytest.raises(Exception):
                await user_repo.create(user2)
        finally:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM users WHERE username LIKE 'test%'")
            await pool.close()

    @pytest.mark.asyncio
    async def test_create_user_with_duplicate_email_fails(self):
        """Test that creating user with duplicate email fails."""
        # Arrange
        pool = await get_fresh_pool()
        user_repo = UserRepository(pool)
        
        user1 = User(
            username="testuser3a",
            email="testuser3@example.com",
            hashed_password="$2b$12$hashedpassword",
        )
        user2 = User(
            username="testuser3b",  # Different username
            email="testuser3@example.com",  # Same email
            hashed_password="$2b$12$hashedpassword",
        )

        try:
            # Act
            await user_repo.create(user1)

            # Assert - should raise exception for duplicate email
            with pytest.raises(Exception):
                await user_repo.create(user2)
        finally:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM users WHERE username LIKE 'test%'")
            await pool.close()


class TestUserRepositoryGetById:
    """Tests for UserRepository.get_by_id()."""

    @pytest.mark.asyncio
    async def test_get_by_id_existing_user(self):
        """Test retrieving an existing user by ID."""
        # Arrange
        pool = await get_fresh_pool()
        user_repo = UserRepository(pool)
        
        user = User(
            username="testuser4",
            email="testuser4@example.com",
            hashed_password="$2b$12$hashedpassword",
            roles=["user", "admin"],
        )
        
        try:
            await user_repo.create(user)

            # Act
            retrieved_user = await user_repo.get_by_id(user.id)

            # Assert
            assert retrieved_user is not None
            assert retrieved_user.id == user.id
            assert retrieved_user.username == user.username
            assert retrieved_user.email == user.email
            assert retrieved_user.hashed_password == user.hashed_password
            assert retrieved_user.roles == user.roles
        finally:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM users WHERE username LIKE 'test%'")
            await pool.close()

    @pytest.mark.asyncio
    async def test_get_by_id_nonexistent_user(self):
        """Test retrieving a non-existent user by ID returns None."""
        # Arrange
        pool = await get_fresh_pool()
        user_repo = UserRepository(pool)
        nonexistent_id = uuid4()

        try:
            # Act
            retrieved_user = await user_repo.get_by_id(nonexistent_id)

            # Assert
            assert retrieved_user is None
        finally:
            await pool.close()


class TestUserRepositoryGetByUsername:
    """Tests for UserRepository.get_by_username()."""

    @pytest.mark.asyncio
    async def test_get_by_username_existing_user(self):
        """Test retrieving an existing user by username."""
        # Arrange
        pool = await get_fresh_pool()
        user_repo = UserRepository(pool)
        
        user = User(
            username="testuser5",
            email="testuser5@example.com",
            hashed_password="$2b$12$hashedpassword",
        )
        
        try:
            await user_repo.create(user)

            # Act
            retrieved_user = await user_repo.get_by_username("testuser5")

            # Assert
            assert retrieved_user is not None
            assert retrieved_user.username == user.username
            assert retrieved_user.email == user.email
        finally:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM users WHERE username LIKE 'test%'")
            await pool.close()

    @pytest.mark.asyncio
    async def test_get_by_username_nonexistent_user(self):
        """Test retrieving a non-existent user by username returns None."""
        # Arrange
        pool = await get_fresh_pool()
        user_repo = UserRepository(pool)
        
        try:
            # Act
            retrieved_user = await user_repo.get_by_username("nonexistent_user")

            # Assert
            assert retrieved_user is None
        finally:
            await pool.close()


class TestUserRepositoryUpdate:
    """Tests for UserRepository.update()."""

    @pytest.mark.asyncio
    async def test_update_user_successfully(self):
        """Test updating an existing user."""
        # Arrange
        pool = await get_fresh_pool()
        user_repo = UserRepository(pool)
        
        user = User(
            username="testuser6",
            email="testuser6@example.com",
            hashed_password="$2b$12$hashedpassword",
            roles=["user"],
        )
        
        try:
            await user_repo.create(user)

            # Modify user
            user.email = "newemail6@example.com"
            user.roles = ["user", "admin"]

            # Act
            updated_user = await user_repo.update(user)

            # Assert
            assert updated_user.email == "newemail6@example.com"
            assert updated_user.roles == ["user", "admin"]

            # Verify in database
            retrieved_user = await user_repo.get_by_id(user.id)
            assert retrieved_user.email == "newemail6@example.com"
            assert retrieved_user.roles == ["user", "admin"]
        finally:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM users WHERE username LIKE 'test%'")
            await pool.close()

    @pytest.mark.asyncio
    async def test_update_nonexistent_user_raises_error(self):
        """Test updating a non-existent user raises UserNotFoundError."""
        # Arrange
        pool = await get_fresh_pool()
        user_repo = UserRepository(pool)
        
        nonexistent_user = User(
            id=uuid4(),
            username="testuser7",
            email="testuser7@example.com",
            hashed_password="$2b$12$hashedpassword",
        )

        try:
            # Act & Assert
            with pytest.raises(UserNotFoundError):
                await user_repo.update(nonexistent_user)
        finally:
            await pool.close()


class TestUserRepositoryDelete:
    """Tests for UserRepository.delete()."""

    @pytest.mark.asyncio
    async def test_delete_user_successfully(self):
        """Test deleting an existing user."""
        # Arrange
        pool = await get_fresh_pool()
        user_repo = UserRepository(pool)
        
        user = User(
            username="testuser8",
            email="testuser8@example.com",
            hashed_password="$2b$12$hashedpassword",
        )
        
        try:
            await user_repo.create(user)

            # Act
            await user_repo.delete(user.id)

            # Assert
            retrieved_user = await user_repo.get_by_id(user.id)
            assert retrieved_user is None
        finally:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM users WHERE username LIKE 'test%'")
            await pool.close()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user_raises_error(self):
        """Test deleting a non-existent user raises UserNotFoundError."""
        # Arrange
        pool = await get_fresh_pool()
        user_repo = UserRepository(pool)
        nonexistent_id = uuid4()

        try:
            # Act & Assert
            with pytest.raises(UserNotFoundError):
                await user_repo.delete(nonexistent_id)
        finally:
            await pool.close()


class TestUserRepositoryGetAll:
    """Tests for UserRepository.get_all()."""

    @pytest.mark.asyncio
    async def test_get_all_users(self):
        """Test retrieving all users with pagination."""
        # Arrange
        pool = await get_fresh_pool()
        user_repo = UserRepository(pool)
        
        user1 = User(username="testuser9a", email="testuser9a@example.com", hashed_password="$2b$12$hashedpassword")
        user2 = User(username="testuser9b", email="testuser9b@example.com", hashed_password="$2b$12$hashedpassword")
        
        try:
            await user_repo.create(user1)
            await user_repo.create(user2)

            # Act
            users = await user_repo.get_all(limit=10, offset=0)
            users_list = list(users)

            # Assert
            assert len(users_list) >= 2  # At least our 2 test users (plus testuser from migration)
            usernames = [u.username for u in users_list]
            assert "testuser9a" in usernames
            assert "testuser9b" in usernames
        finally:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM users WHERE username LIKE 'test%'")
            await pool.close()
