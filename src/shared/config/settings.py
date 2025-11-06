from __future__ import annotations

import os
from dataclasses import dataclass


def _get_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Required environment variable '{name}' is not set and no default provided")
    return value


def _get_int(name: str, default: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None:
        if default is None:
            raise RuntimeError(f"Required environment variable '{name}' is not set and no default provided")
        return default
    return int(raw)


@dataclass(frozen=True)
class AppSettings:
    environment: str
    host: str
    port: int


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    db: str
    user: str
    password: str

    @property
    def dsn(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"


@dataclass(frozen=True)
class RedisSettings:
    host: str
    port: int
    db: int


@dataclass(frozen=True)
class SecuritySettings:
    jwt_secret: str
    jwt_algorithm: str
    jwt_expires_minutes: int


@dataclass(frozen=True)
class Settings:
    app: AppSettings
    db: DatabaseSettings
    redis: RedisSettings
    security: SecuritySettings


def load_settings() -> Settings:
    return Settings(
        app=AppSettings(
            environment=os.getenv("APP_ENV", "local"),
            host=os.getenv("APP_HOST", "0.0.0.0"),
            port=_get_int("APP_PORT", 8000),
        ),
        db=DatabaseSettings(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=_get_int("POSTGRES_PORT", 5432),
            db=os.getenv("POSTGRES_DB", "contextiva"),
            user=os.getenv("POSTGRES_USER", "contextiva"),
            password=os.getenv("POSTGRES_PASSWORD", "changeme"),
        ),
        redis=RedisSettings(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=_get_int("REDIS_PORT", 6379),
            db=_get_int("REDIS_DB", 0),
        ),
        security=SecuritySettings(
            jwt_secret=os.getenv("JWT_SECRET", "change-this-secret"),
            jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            jwt_expires_minutes=_get_int("JWT_EXPIRES_MINUTES", 60),
        ),
    )


