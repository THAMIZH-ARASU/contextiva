"""Unit tests for security utilities (JWT and password hashing)."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from jose import JWTError, jwt

from src.shared.utils.security import (
    create_access_token,
    get_password_hash,
    verify_password,
    verify_token,
)


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_get_password_hash_returns_bcrypt_hash(self) -> None:
        """Test that get_password_hash returns a bcrypt hash."""
        # Arrange
        password = "testpassword123"

        # Act
        hashed = get_password_hash(password)

        # Assert
        assert hashed.startswith("$2b$")
        assert len(hashed) == 60  # bcrypt hashes are 60 chars

    def test_verify_password_with_correct_password(self) -> None:
        """Test password verification with correct password."""
        # Arrange
        password = "mypassword"
        hashed = get_password_hash(password)

        # Act
        result = verify_password(password, hashed)

        # Assert
        assert result is True

    def test_verify_password_with_incorrect_password(self) -> None:
        """Test password verification with incorrect password."""
        # Arrange
        password = "mypassword"
        wrong_password = "wrongpassword"
        hashed = get_password_hash(password)

        # Act
        result = verify_password(wrong_password, hashed)

        # Assert
        assert result is False

    def test_different_passwords_produce_different_hashes(self) -> None:
        """Test that same password hashed twice produces different results."""
        # Arrange
        password = "samepassword"

        # Act
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Assert
        assert hash1 != hash2  # bcrypt uses random salt


class TestJWTTokens:
    """Tests for JWT token creation and verification."""

    def test_create_access_token_with_default_expiration(self) -> None:
        """Test JWT token creation with default expiration."""
        # Arrange
        data = {"sub": "testuser"}

        # Act
        token = create_access_token(data)

        # Assert
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_custom_expiration(self) -> None:
        """Test JWT token creation with custom expiration time."""
        # Arrange
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=15)

        # Act
        token = create_access_token(data, expires_delta=expires_delta)

        # Assert
        assert isinstance(token, str)
        # Verify expiration is set correctly
        from src.shared.config.settings import load_settings
        settings = load_settings()
        payload = jwt.decode(
            token,
            settings.security.jwt_secret,
            algorithms=[settings.security.jwt_algorithm]
        )
        exp = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        diff = (exp - now).total_seconds()
        assert 890 < diff < 910  # Should be around 15 minutes (900 seconds)

    def test_verify_token_with_valid_token(self) -> None:
        """Test token verification with a valid token."""
        # Arrange
        data = {"sub": "testuser", "custom": "data"}
        token = create_access_token(data)

        # Act
        payload = verify_token(token)

        # Assert
        assert payload["sub"] == "testuser"
        assert payload["custom"] == "data"
        assert "exp" in payload
        assert "iat" in payload

    def test_verify_token_with_invalid_token(self) -> None:
        """Test token verification with an invalid token."""
        # Arrange
        invalid_token = "invalid.token.string"

        # Act & Assert
        with pytest.raises(JWTError):
            verify_token(invalid_token)

    def test_verify_token_with_expired_token(self) -> None:
        """Test token verification with an expired token."""
        # Arrange
        data = {"sub": "testuser"}
        # Create token that expired 1 hour ago
        expired_time = datetime.utcnow() - timedelta(hours=1)
        
        with patch('src.shared.utils.security.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = expired_time
            token = create_access_token(data, expires_delta=timedelta(minutes=1))

        # Act & Assert
        with pytest.raises(JWTError):
            verify_token(token)

    def test_token_contains_required_claims(self) -> None:
        """Test that created token contains all required claims."""
        # Arrange
        data = {"sub": "testuser"}

        # Act
        token = create_access_token(data)
        payload = verify_token(token)

        # Assert
        assert "sub" in payload
        assert "exp" in payload  # Expiration
        assert "iat" in payload  # Issued at
        assert payload["sub"] == "testuser"
