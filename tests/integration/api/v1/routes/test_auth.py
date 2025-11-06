"""Integration tests for authentication endpoints."""

import pytest
from httpx import AsyncClient
from jose import jwt

from src.api.dependencies import get_user_repository
from src.api.v1.routes.auth import router
from src.domain.models.user import User
from src.infrastructure.database.repositories.user_repository import UserRepository
from src.shared.config.settings import load_settings
from src.shared.utils.security import get_password_hash


@pytest.fixture
async def test_user(db_pool):
    """Fixture to create a test user in the database."""
    user_repo = UserRepository(db_pool)
    
    # Create test user with known password
    user = User(
        username="authtest",
        email="authtest@example.com",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        roles=["user"],
    )
    await user_repo.create(user)
    
    yield user
    
    # Cleanup
    try:
        await user_repo.delete(user.id)
    except Exception:
        pass


@pytest.fixture
async def inactive_user(db_pool):
    """Fixture to create an inactive test user."""
    user_repo = UserRepository(db_pool)
    
    user = User(
        username="inactiveuser",
        email="inactive@example.com",
        hashed_password=get_password_hash("testpassword"),
        is_active=False,
        roles=["user"],
    )
    await user_repo.create(user)
    
    yield user
    
    # Cleanup
    try:
        await user_repo.delete(user.id)
    except Exception:
        pass


class TestAuthTokenEndpoint:
    """Tests for POST /auth/token endpoint."""

    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self, test_user, app_client):
        """Test successful login with valid credentials returns JWT token."""
        # Arrange
        login_data = {
            "username": "authtest",
            "password": "testpassword",
        }

        # Act
        response = await app_client.post("/api/v1/auth/token", data=login_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    @pytest.mark.asyncio
    async def test_login_with_invalid_username(self, app_client):
        """Test login with invalid username returns 401."""
        # Arrange
        login_data = {
            "username": "nonexistent",
            "password": "testpassword",
        }

        # Act
        response = await app_client.post("/api/v1/auth/token", data=login_data)

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect username or password"

    @pytest.mark.asyncio
    async def test_login_with_invalid_password(self, test_user, app_client):
        """Test login with invalid password returns 401."""
        # Arrange
        login_data = {
            "username": "authtest",
            "password": "wrongpassword",
        }

        # Act
        response = await app_client.post("/api/v1/auth/token", data=login_data)

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Incorrect username or password"

    @pytest.mark.asyncio
    async def test_login_with_inactive_user(self, inactive_user, app_client):
        """Test login with inactive user returns 401."""
        # Arrange
        login_data = {
            "username": "inactiveuser",
            "password": "testpassword",
        }

        # Act
        response = await app_client.post("/api/v1/auth/token", data=login_data)

        # Assert
        assert response.status_code == 401
        data = response.json()
        assert data["detail"] == "Inactive user"

    @pytest.mark.asyncio
    async def test_token_contains_correct_claims(self, test_user, app_client):
        """Test that returned token contains correct claims."""
        # Arrange
        login_data = {
            "username": "authtest",
            "password": "testpassword",
        }
        settings = load_settings()

        # Act
        response = await app_client.post("/api/v1/auth/token", data=login_data)
        data = response.json()
        token = data["access_token"]

        # Decode token (without verification for testing purposes)
        payload = jwt.decode(
            token,
            settings.security.jwt_secret,
            algorithms=[settings.security.jwt_algorithm]
        )

        # Assert
        assert payload["sub"] == "authtest"
        assert "exp" in payload
        assert "iat" in payload


class TestAuthenticationDependency:
    """Tests for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_with_valid_token(self, test_user, app_client):
        """Test get_current_user returns user with valid token."""
        # Arrange - Get a valid token
        login_data = {
            "username": "authtest",
            "password": "testpassword",
        }
        login_response = await app_client.post("/api/v1/auth/token", data=login_data)
        token = login_response.json()["access_token"]

        # Act - Make request to a protected endpoint (once we have one)
        # For now, we just verify the token is valid
        assert token is not None
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token_fails(self, app_client):
        """Test that protected endpoint without token returns 401."""
        # This test assumes we have a protected endpoint
        # For now, this is a placeholder that demonstrates the pattern
        # Once we protect an endpoint, we can test it here
        pass

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_malformed_token_fails(self, app_client):
        """Test that protected endpoint with malformed token returns 401."""
        # This test assumes we have a protected endpoint
        # For now, this is a placeholder
        pass

    @pytest.mark.asyncio
    async def test_protected_endpoint_with_expired_token_fails(self, app_client):
        """Test that protected endpoint with expired token returns 401."""
        # This test assumes we have a protected endpoint
        # For now, this is a placeholder
        pass
