"""Unit tests for User domain model."""

from uuid import UUID, uuid4

import pytest

from src.domain.models.user import User


class TestUserEntity:
    """Tests for User domain entity."""

    def test_create_user_with_all_fields(self) -> None:
        """Test creating a User with all fields specified."""
        # Arrange
        user_id = uuid4()
        username = "johndoe"
        email = "john@example.com"
        hashed_password = "$2b$12$hashedpassword"
        is_active = True
        roles = ["user", "admin"]

        # Act
        user = User(
            id=user_id,
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=is_active,
            roles=roles,
        )

        # Assert
        assert user.id == user_id
        assert user.username == username
        assert user.email == email
        assert user.hashed_password == hashed_password
        assert user.is_active == is_active
        assert user.roles == roles

    def test_create_user_with_minimal_fields(self) -> None:
        """Test creating a User with only required fields."""
        # Arrange
        username = "janedoe"
        email = "jane@example.com"
        hashed_password = "$2b$12$hashedpassword"

        # Act
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
        )

        # Assert
        assert isinstance(user.id, UUID)
        assert user.username == username
        assert user.email == email
        assert user.hashed_password == hashed_password
        assert user.is_active is True  # Default value
        assert user.roles == []  # Default value

    def test_user_requires_username(self) -> None:
        """Test that username is required."""
        # Arrange
        email = "test@example.com"
        hashed_password = "$2b$12$hashedpassword"

        # Act & Assert
        with pytest.raises(ValueError, match="username must be a non-empty string"):
            User(username="", email=email, hashed_password=hashed_password)

    def test_user_requires_email(self) -> None:
        """Test that email is required."""
        # Arrange
        username = "testuser"
        hashed_password = "$2b$12$hashedpassword"

        # Act & Assert
        with pytest.raises(ValueError, match="email must be a non-empty string"):
            User(username=username, email="", hashed_password=hashed_password)

    def test_user_validates_email_format(self) -> None:
        """Test that email format is validated."""
        # Arrange
        username = "testuser"
        invalid_email = "not-an-email"
        hashed_password = "$2b$12$hashedpassword"

        # Act & Assert
        with pytest.raises(ValueError, match="email must be a valid email address"):
            User(username=username, email=invalid_email, hashed_password=hashed_password)

    def test_user_validates_email_format_variations(self) -> None:
        """Test various valid and invalid email formats."""
        # Arrange
        username = "testuser"
        hashed_password = "$2b$12$hashedpassword"

        # Valid emails
        valid_emails = [
            "test@example.com",
            "user.name@example.co.uk",
            "user+tag@example.com",
            "123@example.com",
        ]

        # Act & Assert - valid emails should work
        for email in valid_emails:
            user = User(username=username, email=email, hashed_password=hashed_password)
            assert user.email == email

        # Invalid emails
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@.com",
            "user @example.com",
        ]

        # Act & Assert - invalid emails should raise
        for email in invalid_emails:
            with pytest.raises(ValueError, match="email must be a valid email address"):
                User(username=username, email=email, hashed_password=hashed_password)

    def test_user_requires_hashed_password(self) -> None:
        """Test that hashed_password is required."""
        # Arrange
        username = "testuser"
        email = "test@example.com"

        # Act & Assert
        with pytest.raises(ValueError, match="hashed_password must be provided"):
            User(username=username, email=email, hashed_password="")

    def test_user_roles_must_be_list(self) -> None:
        """Test that roles must be a list."""
        # This test is implicit in the dataclass field definition
        # but we verify the validation logic
        username = "testuser"
        email = "test@example.com"
        hashed_password = "$2b$12$hashedpassword"

        # Should work with list
        user = User(username=username, email=email, hashed_password=hashed_password, roles=["admin"])
        assert user.roles == ["admin"]

    def test_user_roles_validates_non_empty_strings(self) -> None:
        """Test that role strings must be non-empty."""
        # Arrange
        username = "testuser"
        email = "test@example.com"
        hashed_password = "$2b$12$hashedpassword"
        roles_with_empty = ["admin", ""]

        # Act & Assert
        with pytest.raises(ValueError, match="Each role must be a non-empty string"):
            User(username=username, email=email, hashed_password=hashed_password, roles=roles_with_empty)

    def test_user_defaults_to_active(self) -> None:
        """Test that is_active defaults to True."""
        # Arrange
        username = "testuser"
        email = "test@example.com"
        hashed_password = "$2b$12$hashedpassword"

        # Act
        user = User(username=username, email=email, hashed_password=hashed_password)

        # Assert
        assert user.is_active is True

    def test_user_can_be_inactive(self) -> None:
        """Test that user can be created as inactive."""
        # Arrange
        username = "testuser"
        email = "test@example.com"
        hashed_password = "$2b$12$hashedpassword"

        # Act
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=False
        )

        # Assert
        assert user.is_active is False

    def test_user_roles_default_to_empty_list(self) -> None:
        """Test that roles default to empty list."""
        # Arrange
        username = "testuser"
        email = "test@example.com"
        hashed_password = "$2b$12$hashedpassword"

        # Act
        user = User(username=username, email=email, hashed_password=hashed_password)

        # Assert
        assert user.roles == []
        assert isinstance(user.roles, list)
