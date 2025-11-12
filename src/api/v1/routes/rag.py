"""RAG (Retrieval-Augmented Generation) API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_current_user, get_knowledge_repository, get_project_repository
from src.api.v1.schemas.rag import KnowledgeItemResult, RAGQueryRequest, RAGQueryResponse
from src.application.use_cases.knowledge.query_knowledge import QueryKnowledgeUseCase
from src.domain.models.knowledge import IKnowledgeRepository
from src.domain.models.project import IProjectRepository
from src.domain.models.user import User
from src.shared.config.settings import load_settings
from src.shared.utils.errors import ProjectNotFoundError, UnauthorizedAccessError

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/query", response_model=RAGQueryResponse, status_code=status.HTTP_200_OK)
async def query_knowledge(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    knowledge_repo: IKnowledgeRepository = Depends(get_knowledge_repository),
    project_repo: IProjectRepository = Depends(get_project_repository),
) -> RAGQueryResponse:
    """Query knowledge items using RAG (vector similarity search with optional hybrid/re-ranking).
    
    Args:
        request: RAG query request containing project_id, query_text, optional top_k,
                 use_hybrid_search, and use_re_ranking flags.
        current_user: Authenticated user making the request.
        knowledge_repo: Knowledge repository dependency.
        project_repo: Project repository dependency.
        
    Returns:
        RAGQueryResponse containing matched knowledge items with scores.
        
    Raises:
        HTTPException: 404 if project not found, 403 if unauthorized, 422 if validation fails.
    """
    try:
        # Load settings
        settings = load_settings()
        
        # Create and execute use case
        use_case = QueryKnowledgeUseCase(
            knowledge_repo=knowledge_repo,
            project_repo=project_repo,
            settings=settings,
            cache_service=None,  # TODO: Initialize Redis cache service from dependency
        )
        
        result = await use_case.execute(
            project_id=request.project_id,
            query_text=request.query_text,
            user_id=current_user.id,
            top_k=request.top_k,
            use_hybrid_search=request.use_hybrid_search,
            use_re_ranking=request.use_re_ranking,
            use_agentic_rag=request.use_agentic_rag,
        )
        
        # Map domain result to API response
        return RAGQueryResponse(
            results=[
                KnowledgeItemResult(
                    id=item.id,
                    chunk_text=item.chunk_text,
                    similarity_score=similarity_score,
                    bm25_score=bm25_score,
                    rerank_score=rerank_score,
                    metadata=item.metadata,
                    document_id=item.document_id,
                )
                for item, similarity_score, bm25_score, rerank_score in result.results
            ],
            query_id=result.query_id,
            total_results=result.total_results,
            synthesized_answer=result.synthesized_answer,
        )
    except ProjectNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except UnauthorizedAccessError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
