"""Query knowledge use case for RAG retrieval."""

from typing import Any, Optional
from uuid import UUID, uuid4

from src.domain.models.knowledge import IKnowledgeRepository, KnowledgeItem
from src.domain.models.project import IProjectRepository
from src.infrastructure.external.llm.provider_factory import ProviderFactory
from src.shared.config.settings import Settings
from src.shared.utils.errors import ProjectNotFoundError, UnauthorizedAccessError


class QueryKnowledgeResult:
    """Result of a knowledge query operation.
    
    Attributes:
        query_id: Unique identifier for this query.
        results: List of tuples (KnowledgeItem, similarity_score).
        total_results: Total number of results returned.
    """

    def __init__(
        self,
        query_id: UUID,
        results: list[tuple[KnowledgeItem, float]],
        total_results: int,
    ) -> None:
        """Initialize query result.
        
        Args:
            query_id: Unique identifier for this query.
            results: List of tuples (KnowledgeItem, similarity_score).
            total_results: Total number of results returned.
        """
        self.query_id = query_id
        self.results = results
        self.total_results = total_results


class QueryKnowledgeUseCase:
    """Use case for querying knowledge items using RAG."""

    def __init__(
        self,
        knowledge_repo: IKnowledgeRepository,
        project_repo: IProjectRepository,
        settings: Settings,
    ) -> None:
        """Initialize use case with dependencies.
        
        Args:
            knowledge_repo: Repository for knowledge item operations.
            project_repo: Repository for project operations.
            settings: Application settings.
        """
        self.knowledge_repo = knowledge_repo
        self.project_repo = project_repo
        self.settings = settings

    async def execute(
        self,
        project_id: UUID,
        query_text: str,
        user_id: UUID,
        top_k: Optional[int] = None,
    ) -> QueryKnowledgeResult:
        """Execute RAG query to retrieve relevant knowledge items.
        
        Args:
            project_id: UUID of the project to query against.
            query_text: The text query to search for.
            user_id: UUID of the user making the query.
            top_k: Optional number of results to return (uses settings default if not provided).
            
        Returns:
            QueryKnowledgeResult containing matched knowledge items and similarity scores.
            
        Raises:
            ProjectNotFoundError: If the project doesn't exist.
            UnauthorizedAccessError: If user doesn't have access to the project.
        """
        # Step 1: Validate that project exists and user has access
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project {project_id} not found")

        # Check user has access to project (RBAC: owner check)
        if project.owner_id != user_id:
            raise UnauthorizedAccessError(
                f"User {user_id} does not have access to project {project_id}"
            )

        # Step 2: Use top_k from request or fall back to settings default, enforce max
        effective_top_k = top_k if top_k is not None else self.settings.rag.default_top_k
        effective_top_k = min(effective_top_k, self.settings.rag.max_top_k)

        # Step 3: Get embedding provider and generate query embedding
        embedding_provider = ProviderFactory.get_embedding_provider()
        query_embedding = await embedding_provider.embed_text(query_text)

        # Step 4: Perform vector search
        results = await self.knowledge_repo.vector_search(
            project_id=project_id,
            query_embedding=query_embedding,
            top_k=effective_top_k,
        )

        # Step 5: Create result with unique query ID
        query_id = uuid4()
        return QueryKnowledgeResult(
            query_id=query_id,
            results=results,
            total_results=len(results),
        )
