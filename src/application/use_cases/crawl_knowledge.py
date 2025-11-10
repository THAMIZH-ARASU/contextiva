"""Use case for ingesting knowledge from web crawling."""
import hashlib
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.application.services.text_chunker import TextChunker
from src.domain.models.document import Document, DocumentType, IDocumentRepository
from src.domain.models.knowledge import IKnowledgeRepository, KnowledgeItem
from src.infrastructure.external.crawler.crawler_client import WebCrawler
from src.infrastructure.external.llm.providers.base import ILLMProvider
from src.shared.utils.errors import CrawlError, DatabaseError, EmbeddingError

logger = logging.getLogger(__name__)


class CrawlKnowledgeUseCase:
    """Use case for processing and ingesting knowledge from web crawling."""

    def __init__(
        self,
        document_repository: IDocumentRepository,
        knowledge_repository: IKnowledgeRepository,
        web_crawler: WebCrawler,
        text_chunker: TextChunker,
        llm_provider: ILLMProvider,
    ):
        """
        Initialize the use case with required dependencies.

        Args:
            document_repository: Repository for document operations
            knowledge_repository: Repository for knowledge item operations
            web_crawler: Service for crawling web pages
            text_chunker: Service for chunking text
            llm_provider: LLM provider for generating embeddings
        """
        self.document_repository = document_repository
        self.knowledge_repository = knowledge_repository
        self.web_crawler = web_crawler
        self.text_chunker = text_chunker
        self.llm_provider = llm_provider

    async def execute_crawl(
        self, url: str, project_id: UUID, user_id: UUID, respect_robots_txt: bool = True
    ) -> UUID:
        """
        Execute the web crawl knowledge ingestion pipeline.

        Args:
            url: URL to crawl
            project_id: ID of the project to associate the document with
            user_id: ID of the user initiating the crawl
            respect_robots_txt: Whether to respect robots.txt directives

        Returns:
            UUID of the created document

        Raises:
            CrawlError: If crawling fails
            EmbeddingError: If embedding generation fails
            DatabaseError: If database operations fail
        """
        try:
            # Step 1: Crawl the URL and extract content
            logger.info(f"Crawling URL: {url}")
            crawled_content = await self.web_crawler.crawl(url, respect_robots_txt)

            # Step 2: Generate content hash from raw text
            content_hash = hashlib.sha256(crawled_content.text.encode("utf-8")).hexdigest()

            # Step 3: Create document record
            document_name = crawled_content.title or url
            document = Document(
                id=uuid4(),
                project_id=project_id,
                name=document_name,
                type=DocumentType.WEB_CRAWL,
                version="1.0.0",
                content_hash=content_hash,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            # Save document to database
            created_doc = await self.document_repository.create(document)
            logger.info(f"Created document {created_doc.id} for URL {url}")

            # Step 4: Chunk text into segments
            chunks = await self.text_chunker.semantic_chunk(crawled_content.text)
            logger.info(f"Created {len(chunks)} chunks from crawled document {created_doc.id}")

            # Step 5: Generate embeddings and create knowledge items
            knowledge_items: list[KnowledgeItem] = []

            for chunk in chunks:
                try:
                    # Generate embedding for chunk
                    embedding = await self.llm_provider.embed_text(chunk.text)

                    # Merge chunk metadata with crawled metadata
                    chunk_metadata = chunk.to_metadata()
                    chunk_metadata.update(crawled_content.metadata)

                    # Create knowledge item
                    knowledge_item = KnowledgeItem(
                        id=uuid4(),
                        document_id=created_doc.id,
                        chunk_text=chunk.text,
                        chunk_index=chunk.chunk_index,
                        embedding=embedding,
                        metadata=chunk_metadata,
                        created_at=datetime.now(timezone.utc),
                    )
                    knowledge_items.append(knowledge_item)

                except Exception as e:
                    logger.error(f"Failed to generate embedding for chunk {chunk.chunk_index}: {e}")
                    raise EmbeddingError(f"Failed to generate embedding: {str(e)}")

            # Step 6: Batch save knowledge items
            if knowledge_items:
                await self.knowledge_repository.create_batch(knowledge_items)
                logger.info(
                    f"Saved {len(knowledge_items)} knowledge items for document {created_doc.id}"
                )
            else:
                logger.warning(f"No text content extracted from URL {url}")

            return created_doc.id

        except CrawlError:
            raise
        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(f"Failed to crawl and ingest knowledge from {url}: {e}")
            raise DatabaseError(f"Knowledge crawl ingestion failed: {str(e)}")
