"""MCP tools for RAG (Retrieval-Augmented Generation) operations."""

import logging
from typing import Any, Optional
from uuid import UUID

from src.application.use_cases.knowledge.query_knowledge import QueryKnowledgeUseCase
from src.domain.models.user import User
from src.mcp.context import MCPContext
from src.shared.utils.errors import ProjectNotFoundError

logger = logging.getLogger(__name__)


class QueryKnowledgeTool:
    """MCP tool for querying knowledge using RAG.
    
    Provides query_knowledge functionality to MCP clients, supporting
    all RAG features: vector search, hybrid search, re-ranking, and synthesis.
    """

    def __init__(self, context: MCPContext) -> None:
        """Initialize tool with MCP context.
        
        Args:
            context: MCP context for dependency injection.
        """
        self.context = context
        
    async def execute(
        self,
        project_id: str,
        query_text: str,
        top_k: Optional[int] = None,
        use_hybrid_search: bool = False,
        use_re_ranking: bool = False,
        use_agentic_rag: bool = False,
        user: Optional[User] = None,
    ) -> dict[str, Any]:
        """Execute query_knowledge tool.
        
        Args:
            project_id: UUID of the project (required).
            query_text: Query text to search for (required).
            top_k: Number of results to return (optional, uses settings default).
            use_hybrid_search: Enable hybrid vector + keyword search (default: False).
            use_re_ranking: Enable LLM-based re-ranking (default: False).
            use_agentic_rag: Enable synthesis of natural language answer (default: False).
            user: Authenticated user (required).
            
        Returns:
            Dictionary containing knowledge items and optional synthesized answer
            in MCP-compliant format.
            
        Raises:
            ProjectNotFoundError: If project does not exist.
            ValueError: If validation fails.
        """
        if not user:
            raise ValueError("User authentication required for query_knowledge")
            
        # Parse project_id
        try:
            project_uuid = UUID(project_id)
        except ValueError as e:
            raise ValueError(f"Invalid project_id format: {e}")
            
        logger.info(
            f"Querying knowledge in project: {project_id} for user: {user.username}, "
            f"hybrid={use_hybrid_search}, rerank={use_re_ranking}, agentic={use_agentic_rag}"
        )
        
        # Get repositories
        project_repo = await self.context.get_project_repository()
        knowledge_repo = await self.context.get_knowledge_repository()
        
        # Create and execute use case
        use_case = QueryKnowledgeUseCase(
            knowledge_repo=knowledge_repo,
            project_repo=project_repo,
            settings=self.context.settings,
            cache_service=self.context.get_cache_service(),
        )
        
        result = await use_case.execute(
            project_id=project_uuid,
            query_text=query_text,
            user_id=user.id,
            top_k=top_k,
            use_hybrid_search=use_hybrid_search,
            use_re_ranking=use_re_ranking,
            use_agentic_rag=use_agentic_rag,
        )
        
        logger.info(f"Query executed successfully: {result.total_results} results")
        
        # Map results to MCP-compliant format
        knowledge_items = [
            {
                "id": str(item.id),
                "chunk_text": item.chunk_text,
                "similarity_score": similarity_score,
                "bm25_score": bm25_score,
                "rerank_score": rerank_score,
                "metadata": item.metadata,
                "document_id": str(item.document_id),
            }
            for item, similarity_score, bm25_score, rerank_score in result.results
        ]
        
        # Return MCP-compliant response
        return {
            "query_id": str(result.query_id),
            "results": knowledge_items,
            "total_results": result.total_results,
            "synthesized_answer": result.synthesized_answer,
        }
        
    def get_schema(self) -> dict[str, Any]:
        """Get MCP tool schema definition.
        
        Returns:
            MCP tool schema for query_knowledge.
        """
        return {
            "name": "query_knowledge",
            "description": "Query knowledge items using RAG with optional hybrid search, re-ranking, and synthesis",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "UUID of the project to query against",
                        "format": "uuid",
                    },
                    "query_text": {
                        "type": "string",
                        "description": "Query text to search for (1-10000 characters)",
                        "minLength": 1,
                        "maxLength": 10000,
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of results to return (optional, uses settings default)",
                        "minimum": 1,
                    },
                    "use_hybrid_search": {
                        "type": "boolean",
                        "description": "Enable hybrid vector + keyword (BM25) search",
                        "default": False,
                    },
                    "use_re_ranking": {
                        "type": "boolean",
                        "description": "Enable LLM-based re-ranking of results",
                        "default": False,
                    },
                    "use_agentic_rag": {
                        "type": "boolean",
                        "description": "Enable synthesis of natural language answer",
                        "default": False,
                    },
                },
                "required": ["project_id", "query_text"],
            },
        }
