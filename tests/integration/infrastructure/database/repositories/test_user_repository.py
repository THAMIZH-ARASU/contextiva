"""Integration tests for UserRepository."""

from uuid import uuid4

import pytest
import pytest_asyncio
from asyncpg import IntegrityError

from src.domain.models.user import User
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.shared.utils.errors import UserNotFoundError


@pytest.fixture
async def user_repo(db_pool):
    """Fixture to provide UserRepository instance."""
    return UserRepository(db_pool)


@pytest_asyncio.fixture(autouse=True)
async def cleanup_users(db_pool):
    """Cleanup fixture to delete all test users after each test."""
    yield
    # Cleanup: Delete all users after test
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE username LIKE 'test%'")


class TestUserRepositoryCreate:
    """Tests for UserRepository.create()."""

    @pytest.mark.asyncio
    async def test_create_user_successfully(self, user_repo):
        """Test creating a new user successfully."""
        # Arrange
        user = User(
            username="testuser1",
            email="testuser1@example.com",
            hashed_password="$2b$12$hashedpassword",
            roles=["user"],
        )

        # Act
        created_user = await user_repo.create(user)

        # Assert
        assert created_user.id == user.id
        assert created_user.username == user.username
        assert created_user.email == user.email

    @pytest.mark.asyncio
    async def test_create_user_with_duplicate_username_fails(self, user_repo):
        """Test that creating user with duplicate username fails."""
        # Arrange
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

        # Act
        await user_repo.create(user1)

        # Assert
        with pytest.raises(IntegrityError):
            await user_repo.create(user2)

    @pytest.mark.asyncio
    async def test_create_user_with_duplicate_email_fails(self, user_repo):
        """Test that creating user with duplicate email fails."""
        # Arrange
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

        # Act
        await user_repo.create(user1)

        # Assert
        with pytest.raises(IntegrityError):
            await user_repo.create(user2)


class TestUserRepositoryGetById:
    """Tests for UserRepository.get_by_id()."""

    @pytest.mark.asyncio
    async def test_get_by_id_existing_user(self, user_repo):
        """Test retrieving an existing user by ID."""
        # Arrange
        user = User(
            username="testuser4",
            email="testuser4@example.com",
            hashed_password="$2b$12$hashedpassword",
            roles=["user", "admin"],
        )
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

    @pytest.mark.asyncio
    async def test_get_by_id_nonexistent_user(self, user_repo):
        """Test retrieving a non-existent user by ID returns None."""
        # Arrange
        nonexistent_id = uuid4()

        # Act
        retrieved_user = await user_repo.get_by_id(nonexistent_id)

        # Assert
        assert retrieved_user is None


class TestUserRepositoryGetByUsername:
    """Tests for UserRepository.get_by_username()."""

    @pytest.mark.asyncio
    async def test_get_by_username_existing_user(self, user_repo):
        """Test retrieving an existing user by username."""
        # Arrange
        user = User(
            username="testuser5",
            email="testuser5@example.com",
            hashed_password="$2b$12$hashedpassword",
        )
        await user_repo.create(user)

        # Act
        retrieved_user = await user_repo.get_by_username("testuser5")

        # Assert
        assert retrieved_user is not None
        assert retrieved_user.username == user.username
        assert retrieved_user.email == user.email

    @pytest.mark.asyncio
    async def test_get_by_username_nonexistent_user(self, user_repo):
        """Test retrieving a non-existent user by username returns None."""
        # Act
        retrieved_user = await user_repo.get_by_username("nonexistent_user")

        # Assert
        assert retrieved_user is None


class TestUserRepositoryUpdate:
    """Tests for UserRepository.update()."""

    @pytest.mark.asyncio
    async def test_update_user_successfully(self, user_repo):
        """Test updating an existing user."""
        # Arrange
        user = User(
            username="testuser6",
            email="testuser6@example.com",
            hashed_password="$2b$12$hashedpassword",
            roles=["user"],
        )
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

    @pytest.mark.asyncio
    async def test_update_nonexistent_user_raises_error(self, user_repo):
        """Test updating a non-existent user raises UserNotFoundError."""
        # Arrange
        nonexistent_user = User(
            id=uuid4(),
            username="testuser7",
            email="testuser7@example.com",
            hashed_password="$2b$12$hashedpassword",
        )

        # Act & Assert
        with pytest.raises(UserNotFoundError):
            await user_repo.update(nonexistent_user)


class TestUserRepositoryDelete:
    """Tests for UserRepository.delete()."""

    @pytest.mark.asyncio
    async def test_delete_user_successfully(self, user_repo):
        """Test deleting an existing user."""
        # Arrange
        user = User(
            username="testuser8",
            email="testuser8@example.com",
            hashed_password="$2b$12$hashedpassword",
        )
        await user_repo.create(user)

        # Act
        await user_repo.delete(user.id)

        # Assert
        retrieved_user = await user_repo.get_by_id(user.id)
        assert retrieved_user is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user_raises_error(self, user_repo):
        """Test deleting a non-existent user raises UserNotFoundError."""
        # Arrange
        nonexistent_id = uuid4()

        # Act & Assert
        with pytest.raises(UserNotFoundError):
            await user_repo.delete(nonexistent_id)


class TestUserRepositoryGetAll:
    """Tests for UserRepository.get_all()."""

    @pytest.mark.asyncio
    async def test_get_all_users(self, user_repo):
        """Test retrieving all users with pagination."""
        # Arrange
        user1 = User(username="testuser9a", email="testuser9a@example.com", hashed_password="$2b$12$hashedpassword")
        user2 = User(username="testuser9b", email="testuser9b@example.com", hashed_password="$2b$12$hashedpassword")
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
