from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, List, Optional
from uuid import UUID, uuid4


@dataclass(slots=True)
class User:
    """Domain entity for User."""

    # Required fields must come before fields with defaults
    username: str
    email: str
    hashed_password: str
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True
    roles: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate business rules for User entity."""
        if not self.username or not self.username.strip():
            raise ValueError("User.username must be a non-empty string")
        
        if not self.email or not self.email.strip():
            raise ValueError("User.email must be a non-empty string")
        
        # Basic email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, self.email):
            raise ValueError("User.email must be a valid email address")
        
        if not self.hashed_password:
            raise ValueError("User.hashed_password must be provided")
        
        if not isinstance(self.roles, list):
            raise ValueError("User.roles must be a list of strings")
        
        for role in self.roles:
            if not isinstance(role, str) or not role.strip():
                raise ValueError("Each role must be a non-empty string")


class IUserRepository(ABC):
    """Repository interface for User domain entity."""

    @abstractmethod
    async def create(self, user: User) -> User:  # pragma: no cover - interface only
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:  # pragma: no cover
        ...

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:  # pragma: no cover
        ...

    @abstractmethod
    async def get_all(self, limit: int = 100, offset: int = 0) -> Iterable[User]:  # pragma: no cover
        ...

    @abstractmethod
    async def update(self, user: User) -> User:  # pragma: no cover
        ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:  # pragma: no cover
        ...
