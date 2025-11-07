"""Unit tests for settings module (Story 1.1/1.2)."""

import pytest
from src.shared.config.settings import load_settings, DatabaseSettings


class TestDatabaseSettings:
    """Tests for DatabaseSettings."""
    
    def test_dsn_property_formats_connection_string(self, monkeypatch):
        """Test that DSN property formats PostgreSQL connection string correctly."""
        # Set environment variables
        monkeypatch.setenv("POSTGRES_HOST", "localhost")
        monkeypatch.setenv("POSTGRES_PORT", "5432")
        monkeypatch.setenv("POSTGRES_DB", "testdb")
        monkeypatch.setenv("POSTGRES_USER", "testuser")
        monkeypatch.setenv("POSTGRES_PASSWORD", "testpass")
        
        settings = load_settings()
        db_settings = settings.db
        
        assert db_settings.dsn.startswith("postgresql://")
        assert "testuser" in db_settings.dsn
        assert "testdb" in db_settings.dsn
        assert "localhost" in db_settings.dsn
        assert "5432" in db_settings.dsn


class TestLoadSettings:
    """Tests for load_settings function."""
    
    def test_load_settings_returns_all_settings_groups(self, monkeypatch):
        """Test that load_settings returns all required settings groups."""
        # Set minimal required env vars
        monkeypatch.setenv("POSTGRES_HOST", "localhost")
        monkeypatch.setenv("POSTGRES_PORT", "5432")
        monkeypatch.setenv("POSTGRES_DB", "test")
        monkeypatch.setenv("POSTGRES_USER", "test")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
        
        settings = load_settings()
        
        assert hasattr(settings, "app")
        assert hasattr(settings, "db")
        assert hasattr(settings, "redis")
        assert hasattr(settings, "security")
    
    def test_settings_uses_defaults_when_env_not_set(self, monkeypatch):
        """Test that settings use default values when environment variables are not set."""
        # Set only required vars
        monkeypatch.setenv("POSTGRES_HOST", "localhost")
        monkeypatch.setenv("POSTGRES_PORT", "5432")
        monkeypatch.setenv("POSTGRES_DB", "test")
        monkeypatch.setenv("POSTGRES_USER", "test")
        monkeypatch.setenv("POSTGRES_PASSWORD", "test")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
        
        # Unset optional vars
        monkeypatch.delenv("APP_ENV", raising=False)
        monkeypatch.delenv("APP_HOST", raising=False)
        monkeypatch.delenv("APP_PORT", raising=False)
        
        settings = load_settings()
        
        # Should have default values
        assert settings.app.environment in ["local", "development", "production"]
        assert settings.app.host is not None
        assert settings.app.port is not None
