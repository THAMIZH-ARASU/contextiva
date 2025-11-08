"""Use case for ingesting knowledge from files."""
import hashlib
import logging
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile

from src.application.services.text_chunker import TextChunker
from src.application.services.text_extractor import TextExtractor
from src.domain.models.document import Document, DocumentType, IDocumentRepository
from src.domain.models.knowledge import IKnowledgeRepository, KnowledgeItem
from src.infrastructure.external.llm.providers.base import ILLMProvider
from src.shared.utils.errors import DatabaseError, EmbeddingError, TextExtractionError

logger = logging.getLogger(__name__)


class IngestKnowledgeUseCase:
    """Use case for processing and ingesting knowledge from uploaded files."""

    def __init__(
        self,
        document_repository: IDocumentRepository,
        knowledge_repository: IKnowledgeRepository,
        text_extractor: TextExtractor,
        text_chunker: TextChunker,
        llm_provider: ILLMProvider,
    ):
        """
        Initialize the use case with required dependencies.

        Args:
            document_repository: Repository for document operations
            knowledge_repository: Repository for knowledge item operations
            text_extractor: Service for extracting text from files
            text_chunker: Service for chunking text
            llm_provider: LLM provider for generating embeddings
        """
        self.document_repository = document_repository
        self.knowledge_repository = knowledge_repository
        self.text_extractor = text_extractor
        self.text_chunker = text_chunker
        self.llm_provider = llm_provider

    async def execute(self, file: UploadFile, project_id: UUID) -> UUID:
        """
        Execute the knowledge ingestion pipeline.

        Args:
            file: Uploaded file to process
            project_id: ID of the project to associate the document with

        Returns:
            UUID of the created document

        Raises:
            TextExtractionError: If text extraction fails
            EmbeddingError: If embedding generation fails
            DatabaseError: If database operations fail
        """
        try:
            # Read file content
            file_content = await file.read()
            content_hash = hashlib.sha256(file_content).hexdigest()

            # Detect file type from extension
            file_extension = Path(file.filename or "").suffix.lower()
            doc_type_map = {
                ".md": DocumentType.MARKDOWN,
                ".pdf": DocumentType.PDF,
                ".docx": DocumentType.DOCX,
                ".html": DocumentType.HTML,
            }
            doc_type = doc_type_map.get(file_extension, DocumentType.TEXT)

            # Create document record
            document = Document(
                id=uuid4(),
                project_id=project_id,
                name=file.filename or "untitled",
                type=doc_type,
                version="1.0.0",
                content_hash=content_hash,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            # Save document to database
            created_doc = await self.document_repository.create(document)
            logger.info(f"Created document {created_doc.id} for file {file.filename}")

            # Extract text from file
            text = await self.text_extractor.extract(file_content, file.filename or "")
            logger.info(f"Extracted {len(text)} characters from {file.filename}")

            # Chunk text into segments
            chunks = await self.text_chunker.semantic_chunk(text)
            logger.info(f"Created {len(chunks)} chunks from document {created_doc.id}")

            # Generate embeddings and create knowledge items
            knowledge_items: list[KnowledgeItem] = []

            for chunk in chunks:
                try:
                    # Generate embedding for chunk
                    embedding = await self.llm_provider.embed_text(chunk.text)

                    # Create knowledge item
                    knowledge_item = KnowledgeItem(
                        id=uuid4(),
                        document_id=created_doc.id,
                        chunk_text=chunk.text,
                        chunk_index=chunk.chunk_index,
                        embedding=embedding,
                        metadata=chunk.to_metadata(),
                        created_at=datetime.utcnow(),
                    )
                    knowledge_items.append(knowledge_item)

                except Exception as e:
                    logger.error(f"Failed to generate embedding for chunk {chunk.chunk_index}: {e}")
                    raise EmbeddingError(f"Failed to generate embedding: {str(e)}")

            # Batch save knowledge items
            if knowledge_items:
                await self.knowledge_repository.create_batch(knowledge_items)
                logger.info(
                    f"Saved {len(knowledge_items)} knowledge items for document {created_doc.id}"
                )

            return created_doc.id

        except TextExtractionError:
            raise
        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(f"Failed to ingest knowledge from {file.filename}: {e}")
            raise DatabaseError(f"Knowledge ingestion failed: {str(e)}")
