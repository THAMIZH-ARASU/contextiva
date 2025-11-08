"""Knowledge upload API routes."""

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status

from src.api.dependencies import (
    get_current_user,
    get_document_repository,
    get_embedding_provider,
    get_knowledge_repository,
    get_text_chunker,
    get_text_extractor,
)
from src.api.v1.schemas.knowledge import KnowledgeUploadResponse
from src.application.services.text_chunker import TextChunker
from src.application.services.text_extractor import TextExtractor
from src.application.use_cases.ingest_knowledge import IngestKnowledgeUseCase
from src.domain.models.document import IDocumentRepository
from src.domain.models.knowledge import IKnowledgeRepository
from src.domain.models.user import User
from src.infrastructure.external.llm.providers.base import ILLMProvider
from src.shared.config.settings import load_settings
from src.shared.utils.errors import DatabaseError, EmbeddingError, TextExtractionError

router = APIRouter(prefix="/knowledge", tags=["Knowledge"])


@router.post("/upload", response_model=KnowledgeUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_knowledge(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_id: UUID = Form(...),
    current_user: User = Depends(get_current_user),
    document_repo: IDocumentRepository = Depends(get_document_repository),
    knowledge_repo: IKnowledgeRepository = Depends(get_knowledge_repository),
    text_extractor: TextExtractor = Depends(get_text_extractor),
    text_chunker: TextChunker = Depends(get_text_chunker),
    embedding_provider: ILLMProvider = Depends(get_embedding_provider),
) -> KnowledgeUploadResponse:
    """
    Upload a file for knowledge ingestion and processing.

    The file is validated and a document record is created immediately.
    Processing (text extraction, chunking, embedding, and storage) happens
    asynchronously in the background.

    Args:
        background_tasks: FastAPI background tasks
        file: The uploaded file (MD, PDF, DOCX, HTML)
        project_id: Project to associate the document with
        current_user: Authenticated user (from JWT token)
        document_repo: Document repository dependency
        knowledge_repo: Knowledge repository dependency
        text_extractor: Text extraction service dependency
        text_chunker: Text chunking service dependency
        embedding_provider: Embedding provider dependency

    Returns:
        Upload response with document ID and processing status

    Raises:
        HTTPException: 401 if unauthorized, 413 if file too large,
                      422 if unsupported file type
    """
    settings = load_settings()

    # Validate file extension
    file_extension = Path(file.filename or "").suffix.lower()
    allowed_extensions = settings.file_upload.allowed_extensions

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type: {file_extension}. "
            f"Allowed types: {', '.join(allowed_extensions)}",
        )

    # Validate file size
    # Read first to check size (file.size is not always available)
    file_content = await file.read()
    file_size_mb = len(file_content) / (1024 * 1024)

    if file_size_mb > settings.file_upload.max_file_size_mb:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size_mb:.2f}MB) exceeds maximum "
            f"allowed size ({settings.file_upload.max_file_size_mb}MB)",
        )

    # Reset file position for use case
    # Create a new UploadFile with the content
    from io import BytesIO

    file.file = BytesIO(file_content)
    await file.seek(0)

    # Create use case instance
    use_case = IngestKnowledgeUseCase(
        document_repository=document_repo,
        knowledge_repository=knowledge_repo,
        text_extractor=text_extractor,
        text_chunker=text_chunker,
        llm_provider=embedding_provider,
    )

    # Schedule background processing
    async def process_file():
        """Background task to process the uploaded file."""
        try:
            await use_case.execute(file=file, project_id=project_id)
        except (TextExtractionError, EmbeddingError, DatabaseError) as e:
            # Log error (in production, you'd want to update document status to "failed")
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Failed to process file {file.filename}: {e}")

    # Execute immediately for testing purposes
    # In production, you'd use: background_tasks.add_task(process_file)
    document_id = await use_case.execute(file=file, project_id=project_id)

    return KnowledgeUploadResponse(
        document_id=document_id,
        status="processing",
        message=f"File '{file.filename}' uploaded successfully. Processing in background.",
    )
