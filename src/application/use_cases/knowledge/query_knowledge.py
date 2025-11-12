"""Query knowledge use case for RAG retrieval."""

import logging
from typing import Any, Optional
from uuid import UUID, uuid4

from src.application.services.hybrid_search_service import HybridSearchService
from src.application.services.reranking_service import RerankingService
from src.application.services.synthesis_service import SynthesisService
from src.domain.models.knowledge import IKnowledgeRepository, KnowledgeItem
from src.domain.models.project import IProjectRepository
from src.infrastructure.cache.redis_cache import RedisCacheService
from src.infrastructure.external.llm.provider_factory import ProviderFactory
from src.shared.config.settings import Settings
from src.shared.utils.errors import ProjectNotFoundError, UnauthorizedAccessError

logger = logging.getLogger(__name__)


class QueryKnowledgeResult:
    """Result of a knowledge query operation.
    
    Attributes:
        query_id: Unique identifier for this query.
        results: List of tuples (KnowledgeItem, similarity_score, bm25_score, rerank_score).
        total_results: Total number of results returned.
        synthesized_answer: Optional synthesized natural language answer.
    """

    def __init__(
        self,
        query_id: UUID,
        results: list[tuple[KnowledgeItem, float, Optional[float], Optional[float]]],
        total_results: int,
        synthesized_answer: Optional[str] = None,
    ) -> None:
        """Initialize query result.
        
        Args:
            query_id: Unique identifier for this query.
            results: List of tuples (KnowledgeItem, similarity_score, bm25_score, rerank_score).
            total_results: Total number of results returned.
            synthesized_answer: Optional synthesized natural language answer.
        """
        self.query_id = query_id
        self.results = results
        self.total_results = total_results
        self.synthesized_answer = synthesized_answer


class QueryKnowledgeUseCase:
    """Use case for querying knowledge items using RAG."""

    def __init__(
        self,
        knowledge_repo: IKnowledgeRepository,
        project_repo: IProjectRepository,
        settings: Settings,
        cache_service: Optional[RedisCacheService] = None,
    ) -> None:
        """Initialize use case with dependencies.
        
        Args:
            knowledge_repo: Repository for knowledge item operations.
            project_repo: Repository for project operations.
            settings: Application settings.
            cache_service: Optional Redis cache service for query result caching.
        """
        self.knowledge_repo = knowledge_repo
        self.project_repo = project_repo
        self.settings = settings
        self.cache_service = cache_service
        self.hybrid_search_service = HybridSearchService()
        self.reranking_service = RerankingService()
        self.synthesis_service = SynthesisService()

    async def execute(
        self,
        project_id: UUID,
        query_text: str,
        user_id: UUID,
        top_k: Optional[int] = None,
        use_hybrid_search: bool = False,
        use_re_ranking: bool = False,
        use_agentic_rag: bool = False,
    ) -> QueryKnowledgeResult:
        """Execute RAG query to retrieve relevant knowledge items.
        
        Args:
            project_id: UUID of the project to query against.
            query_text: The text query to search for.
            user_id: UUID of the user making the query.
            top_k: Optional number of results to return (uses settings default if not provided).
            use_hybrid_search: Enable hybrid vector + keyword search.
            use_re_ranking: Enable LLM-based re-ranking of results.
            use_agentic_rag: Enable synthesis of natural language answer.
            
        Returns:
            QueryKnowledgeResult containing matched knowledge items and scores.
            
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

        # Override flags with settings if defaults are set
        if self.settings.rag.use_hybrid_search and not use_hybrid_search:
            use_hybrid_search = True
        if self.settings.rag.use_reranking and not use_re_ranking:
            use_re_ranking = True
        if self.settings.rag.use_agentic_rag and not use_agentic_rag:
            use_agentic_rag = True

        # Step 3: Check cache if enabled
        cache_key = None
        if self.cache_service and self.settings.rag.cache_enabled:
            cache_key = self.cache_service.generate_cache_key(
                project_id=project_id,
                query_text=query_text,
                use_hybrid=use_hybrid_search,
                use_rerank=use_re_ranking,
                use_agentic=use_agentic_rag,
                top_k=effective_top_k,
                prefix=self.settings.rag.cache_key_prefix,
            )

            cached_result = await self.cache_service.get(cache_key)
            if cached_result:
                logger.info(f"Cache HIT for query on project {project_id}")
                return self._deserialize_cache_result(cached_result)

        logger.info(f"Cache MISS for query on project {project_id}")

        # Step 4: Get embedding provider and generate query embedding
        embedding_provider = ProviderFactory.get_embedding_provider()
        query_embedding = await embedding_provider.embed_text(query_text)

        # Step 5: Perform search (vector or hybrid)
        if use_hybrid_search:
            # Perform both vector and keyword search
            vector_results = await self.knowledge_repo.vector_search(
                project_id=project_id,
                query_embedding=query_embedding,
                top_k=effective_top_k,
            )

            keyword_results = await self.knowledge_repo.keyword_search(
                project_id=project_id,
                query_text=query_text,
                top_k=effective_top_k,
            )

            # Merge using hybrid search service
            search_results = await self.hybrid_search_service.merge_results(
                vector_results=vector_results,
                keyword_results=keyword_results,
                weight_vector=self.settings.rag.hybrid_search_weight_vector,
                weight_bm25=self.settings.rag.hybrid_search_weight_bm25,
            )
        else:
            # Vector search only
            search_results = await self.knowledge_repo.vector_search(
                project_id=project_id,
                query_embedding=query_embedding,
                top_k=effective_top_k,
            )

        # Step 6: Apply re-ranking if enabled
        if use_re_ranking and search_results:
            llm_provider = ProviderFactory.get_llm_provider(
                model_name=self.settings.rag.reranking_model
            )

            # Extract KnowledgeItems for re-ranking (limit to reranking_top_k)
            chunks_to_rerank = [
                item for item, _ in search_results[: self.settings.rag.reranking_top_k]
            ]

            # Re-rank
            reranked_results = await self.reranking_service.rerank_chunks(
                query_text=query_text,
                chunks=chunks_to_rerank,
                llm_provider=llm_provider,
                top_k=len(chunks_to_rerank),  # Re-rank all selected chunks
            )

            # Map scores back
            final_results = self._combine_scores(
                search_results, reranked_results, use_hybrid_search
            )
        else:
            # No re-ranking - convert to final format
            if use_hybrid_search:
                # Hybrid search: similarity_score is RRF combined score
                final_results = [
                    (item, score, None, None) for item, score in search_results
                ]
            else:
                # Vector only: similarity_score is cosine similarity
                final_results = [
                    (item, score, None, None) for item, score in search_results
                ]

        # Step 7: Apply synthesis if enabled
        synthesized_answer = None
        if use_agentic_rag and final_results:
            try:
                # Get LLM provider for synthesis
                llm_provider = ProviderFactory.get_llm_provider(
                    model_name=self.settings.rag.agentic_rag_model
                )

                # Extract KnowledgeItems from final_results
                chunks_for_synthesis = [item for item, _, _, _ in final_results]

                # Synthesize answer
                synthesized_answer = await self.synthesis_service.synthesize(
                    query=query_text,
                    chunks=chunks_for_synthesis,
                    llm_provider=llm_provider,
                    settings=self.settings.rag,
                )

                if synthesized_answer:
                    logger.info(f"Successfully synthesized answer for query on project {project_id}")
                else:
                    logger.warning(f"Synthesis returned None for query on project {project_id}")
            except Exception as e:
                # Graceful degradation: Log error but don't fail the query
                logger.error(f"Synthesis failed for query on project {project_id}: {e}")
                synthesized_answer = None

        # Step 8: Create result with unique query ID
        query_id = uuid4()
        result = QueryKnowledgeResult(
            query_id=query_id,
            results=final_results,
            total_results=len(final_results),
            synthesized_answer=synthesized_answer,
        )

        # Step 9: Cache result if enabled
        if cache_key and self.cache_service and self.settings.rag.cache_enabled:
            await self._cache_result(cache_key, result)

        return result

    def _combine_scores(
        self,
        search_results: list[tuple[KnowledgeItem, float]],
        reranked_results: list[tuple[KnowledgeItem, float]],
        is_hybrid: bool,
    ) -> list[tuple[KnowledgeItem, float, Optional[float], Optional[float]]]:
        """Combine search and re-ranking scores.

        Args:
            search_results: Original search results with scores
            reranked_results: Re-ranked results with new scores
            is_hybrid: Whether hybrid search was used

        Returns:
            List of (item, similarity_score, bm25_score, rerank_score)
        """
        # Build lookup map for search scores
        search_scores = {item.id: score for item, score in search_results}

        # Build result list with combined scores
        results = []
        for item, rerank_score in reranked_results:
            similarity_score = search_scores.get(item.id, 0.0)
            # For hybrid search, similarity_score is the combined score
            # We don't have separate vector/keyword scores after merge
            # So we use None for bm25_score unless we track it separately
            results.append((item, similarity_score, None, rerank_score))

        return results

    def _deserialize_cache_result(self, cached_data: str) -> QueryKnowledgeResult:
        """Deserialize cached query result from JSON.

        Args:
            cached_data: JSON string from cache

        Returns:
            QueryKnowledgeResult instance

        Raises:
            ValueError: If deserialization fails
        """
        import json
        from datetime import datetime

        try:
            data = json.loads(cached_data)
            
            # Deserialize results
            results = []
            for item_data in data.get("results", []):
                # Deserialize KnowledgeItem
                knowledge_item = KnowledgeItem(
                    id=UUID(item_data["id"]),
                    document_id=UUID(item_data["document_id"]),
                    chunk_text=item_data["chunk_text"],
                    chunk_index=item_data["chunk_index"],
                    embedding=item_data["embedding"],
                    metadata=item_data["metadata"],
                    created_at=datetime.fromisoformat(item_data["created_at"]),
                )
                
                # Extract scores (may be None)
                similarity_score = item_data["similarity_score"]
                bm25_score = item_data.get("bm25_score")
                rerank_score = item_data.get("rerank_score")
                
                results.append((knowledge_item, similarity_score, bm25_score, rerank_score))
            
            return QueryKnowledgeResult(
                query_id=UUID(data["query_id"]),
                results=results,
                total_results=data["total_results"],
                synthesized_answer=data.get("synthesized_answer"),
            )
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to deserialize cached result: {e}")
            raise ValueError(f"Invalid cached data format: {e}")

    async def _cache_result(self, cache_key: str, result: QueryKnowledgeResult) -> None:
        """Cache query result as JSON.

        Args:
            cache_key: Cache key
            result: Query result to cache
        """
        import json

        try:
            # Serialize results to JSON-compatible format
            serialized_results = []
            for item, similarity_score, bm25_score, rerank_score in result.results:
                serialized_item = {
                    "id": str(item.id),
                    "document_id": str(item.document_id),
                    "chunk_text": item.chunk_text,
                    "chunk_index": item.chunk_index,
                    "embedding": item.embedding,
                    "metadata": item.metadata,
                    "created_at": item.created_at.isoformat(),
                    "similarity_score": similarity_score,
                    "bm25_score": bm25_score,
                    "rerank_score": rerank_score,
                }
                serialized_results.append(serialized_item)

            cache_data = json.dumps({
                "query_id": str(result.query_id),
                "results": serialized_results,
                "total_results": result.total_results,
                "synthesized_answer": result.synthesized_answer,
            })

            await self.cache_service.set(
                cache_key, cache_data, self.settings.rag.cache_ttl
            )
            logger.debug(f"Cached query result with {result.total_results} items")
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to cache result: {e}")
