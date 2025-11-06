from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterable, List, Optional
from uuid import UUID, uuid4


VALID_STATUSES = {"Active", "Archived"}


@dataclass(slots=True)
class Project:
    """Domain entity for Project (aggregate root)."""

    # Required fields must come before fields with defaults
    name: str
    id: UUID = field(default_factory=uuid4)
    description: Optional[str] = None
    status: str = field(default="Active")
    tags: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Project.name must be a non-empty string")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Project.status must be one of {sorted(VALID_STATUSES)}")
        if self.tags is not None:
            if not isinstance(self.tags, list):
                raise ValueError("Project.tags must be a list of strings if provided")
            for tag in self.tags:
                if not isinstance(tag, str) or not tag:
                    raise ValueError("Each tag must be a non-empty string")
                if not re.match(r"^[A-Za-z0-9_-]+$", tag):
                    raise ValueError("Tags may only contain letters, numbers, underscore, and hyphen")


class IProjectRepository(ABC):
    """Repository interface for Project domain entity."""

    @abstractmethod
    async def create(self, project: Project) -> Project:  # pragma: no cover - interface only
        ...

    @abstractmethod
    async def get_by_id(self, project_id: UUID) -> Optional[Project]:  # pragma: no cover
        ...

    @abstractmethod
    async def get_all(self, limit: int = 100, offset: int = 0) -> Iterable[Project]:  # pragma: no cover
        ...

    @abstractmethod
    async def update(self, project: Project) -> Project:  # pragma: no cover
        ...

    @abstractmethod
    async def delete(self, project_id: UUID) -> None:  # pragma: no cover
        ...


