"""Document management API routes."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.api.dependencies import get_current_user, get_document_repository
from src.api.v1.schemas.document import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    DocumentVersionCreate,
)
from src.domain.models.document import Document, IDocumentRepository
from src.domain.models.user import User
from src.shared.utils.versioning import bump_version

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    document_data: DocumentCreate,
    current_user: User = Depends(get_current_user),
    document_repo: IDocumentRepository = Depends(get_document_repository),
) -> DocumentResponse:
    """
    Create a new document with version v1.0.0.
    
    Args:
        document_data: The document creation data
        current_user: The authenticated user (from JWT token)
        document_repo: The document repository dependency
        
    Returns:
        The created document
        
    Raises:
        HTTPException: 401 if unauthorized, 422 if validation fails
    """
    # Create domain entity from schema (initial version is v1.0.0)
    document = Document(
        id=uuid4(),
        project_id=document_data.project_id,
        name=document_data.name,
        type=document_data.type,
        version="v1.0.0",
        content_hash=document_data.content_hash,
        created_at=None,  # Will be set by repository
        updated_at=None,  # Will be set by repository
    )
    
    # Persist to database
    created_document = await document_repo.create(document)
    
    # Return response schema
    return DocumentResponse.model_validate(created_document)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    document_repo: IDocumentRepository = Depends(get_document_repository),
) -> DocumentListResponse:
    """
    List all documents for a project with pagination.
    
    Args:
        project_id: Project identifier (required query parameter)
        skip: Number of documents to skip (default: 0)
        limit: Maximum number of documents to return (default: 100, max: 1000)
        current_user: The authenticated user (from JWT token)
        document_repo: The document repository dependency
        
    Returns:
        List of documents with pagination metadata
        
    Raises:
        HTTPException: 401 if unauthorized
    """
    # Enforce max limit to prevent abuse
    if limit > 1000:
        limit = 1000
    
    # Fetch documents from repository
    documents = await document_repo.get_by_project(
        project_id=project_id, skip=skip, limit=limit
    )
    
    # Get total count (for now, use length of returned documents as approximation)
    # TODO: Add count query to repository for accurate total
    total = len(documents) + skip
    
    # Convert to response schemas
    document_responses = [DocumentResponse.model_validate(doc) for doc in documents]
    
    return DocumentListResponse(
        documents=document_responses, total=total, skip=skip, limit=limit
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    version: str | None = None,
    current_user: User = Depends(get_current_user),
    document_repo: IDocumentRepository = Depends(get_document_repository),
) -> DocumentResponse:
    """
    Retrieve a specific document.
    
    Args:
        document_id: Document identifier
        version: Optional version to retrieve (defaults to latest)
        current_user: The authenticated user (from JWT token)
        document_repo: The document repository dependency
        
    Returns:
        The requested document
        
    Raises:
        HTTPException: 401 if unauthorized, 404 if document not found
    """
    # Retrieve document from repository
    document = await document_repo.get_by_id(document_id)
    
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    
    # If version specified, get that specific version
    # TODO: Implement get_by_version in repository if needed
    # For now, we only support latest version
    
    return DocumentResponse.model_validate(document)


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: UUID,
    update_data: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    document_repo: IDocumentRepository = Depends(get_document_repository),
) -> DocumentResponse:
    """
    Update document metadata (name, tags).
    
    Args:
        document_id: Document identifier
        update_data: The document update data
        current_user: The authenticated user (from JWT token)
        document_repo: The document repository dependency
        
    Returns:
        The updated document
        
    Raises:
        HTTPException: 401 if unauthorized, 404 if document not found, 422 if validation fails
    """
    # Retrieve existing document
    document = await document_repo.get_by_id(document_id)
    
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    
    # Update only provided fields (partial update)
    updated_document = Document(
        id=document.id,
        project_id=document.project_id,
        name=update_data.name if update_data.name is not None else document.name,
        type=document.type,
        version=document.version,
        content_hash=document.content_hash,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
    
    # Persist updates
    result = await document_repo.update(updated_document)
    
    return DocumentResponse.model_validate(result)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_repo: IDocumentRepository = Depends(get_document_repository),
) -> Response:
    """
    Delete a document (CASCADE deletes all linked knowledge items).
    
    Args:
        document_id: Document identifier
        current_user: The authenticated user (from JWT token)
        document_repo: The document repository dependency
        
    Returns:
        204 No Content
        
    Raises:
        HTTPException: 401 if unauthorized, 404 if document not found
    """
    # Delete document
    deleted = await document_repo.delete(document_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{document_id}/version",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_version(
    document_id: UUID,
    version_data: DocumentVersionCreate,
    current_user: User = Depends(get_current_user),
    document_repo: IDocumentRepository = Depends(get_document_repository),
) -> DocumentResponse:
    """
    Create a new version of an existing document.
    
    Args:
        document_id: Document identifier
        version_data: The version creation data (content_hash, bump_type)
        current_user: The authenticated user (from JWT token)
        document_repo: The document repository dependency
        
    Returns:
        The new document version
        
    Raises:
        HTTPException: 401 if unauthorized, 404 if document not found, 422 if version invalid
    """
    # Retrieve existing document
    existing_document = await document_repo.get_by_id(document_id)
    
    if existing_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )
    
    # Bump version using utility function
    try:
        new_version = bump_version(existing_document.version, version_data.bump_type)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid version format: {str(e)}",
        ) from e
    
    # Create new document version (new row with same name, project_id, but new version)
    new_document = Document(
        id=uuid4(),  # New ID for new version
        project_id=existing_document.project_id,
        name=existing_document.name,
        type=existing_document.type,
        version=new_version,
        content_hash=version_data.content_hash,
        created_at=None,  # Will be set by repository
        updated_at=None,  # Will be set by repository
    )
    
    # Persist new version
    created_version = await document_repo.create(new_document)
    
    return DocumentResponse.model_validate(created_version)
