from __future__ import annotations

from typing import Iterable, List, Optional
from uuid import UUID

from src.domain.models.project import IProjectRepository, Project
from src.shared.infrastructure.database.connection import init_pool
from src.shared.utils.errors import ProjectNotFoundError


class ProjectRepository(IProjectRepository):
    async def create(self, project: Project) -> Project:
        pool = await init_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO projects (id, name, description, status, tags, owner_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                project.id,
                project.name,
                project.description,
                project.status,
                project.tags,
                project.owner_id,
            )
            if row is None:
                # This should not happen under normal circumstances
                raise RuntimeError("Failed to insert project")
        return project

    async def get_by_id(self, project_id: UUID) -> Optional[Project]:
        pool = await init_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, description, status, tags, owner_id FROM projects WHERE id = $1",
                project_id,
            )
            if row is None:
                return None
            return Project(
                id=row["id"],
                name=row["name"],
                owner_id=row["owner_id"],
                description=row["description"],
                status=row["status"],
                tags=list(row["tags"]) if row["tags"] is not None else None,
            )

    async def get_all(self, limit: int = 100, offset: int = 0) -> Iterable[Project]:
        pool = await init_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, description, status, tags, owner_id
                FROM projects
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        results: List[Project] = []
        for row in rows:
            results.append(
                Project(
                    id=row["id"],
                    name=row["name"],
                    owner_id=row["owner_id"],
                    description=row["description"],
                    status=row["status"],
                    tags=list(row["tags"]) if row["tags"] is not None else None,
                )
            )
        return results

    async def update(self, project: Project) -> Project:
        pool = await init_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE projects
                SET name = $2, description = $3, status = $4, tags = $5, owner_id = $6, updated_at = now()
                WHERE id = $1
                RETURNING id
                """,
                project.id,
                project.name,
                project.description,
                project.status,
                project.tags,
                project.owner_id,
            )
            if row is None:
                raise ProjectNotFoundError(str(project.id))
        return project

    async def delete(self, project_id: UUID) -> None:
        pool = await init_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("DELETE FROM projects WHERE id = $1 RETURNING 1", project_id)
            if row is None:
                raise ProjectNotFoundError(str(project_id))


