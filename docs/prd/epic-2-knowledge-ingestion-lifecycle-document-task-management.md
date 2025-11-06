# Epic 2: Knowledge Ingestion & Lifecycle (Document & Task Management)
**Epic Goal**: Build on the "Project" foundation to implement the complete Document and Task management systems, and deliver the full knowledge ingestion pipeline. This includes setting up the flexible LLM/Embedding provider factory and implementing both file and web-based ingestion, processing (chunking/embedding), and storage.

## Story 2.1: Core Domain Models (Document, Task, KnowledgeItem)
As a AI Agent Developer, I want the Document, Task, and KnowledgeItem domain models and repositories defined, so that I can build the core ingestion and tracking logic.

### Acceptance Criteria:
- The Document entity is defined in `src/domain/models/document.py`, including attributes for `project_id`, `name`, `type`, `version`, and `content_hash`. It must support semantic versioning (NFR1, FR3).
- The Task entity is defined in `src/domain/models/task.py`, including attributes for `project_id`, `title`, `status`, `priority`, `assignee`, and `dependencies` (NFR1, FR5).
- The KnowledgeItem entity is defined in `src/domain/models/knowledge.py`, including `document_id`, `chunk_text`, `embedding` (using pgvector's Vector type), and `metadata`.
- Respective repository interfaces (IDocumentRepository, ITaskRepository, IKnowledgeRepository) and concrete PostgreSQL implementations are created (NFR1).
- Alembic migrations are created to establish the new documents, tasks, and knowledge_items tables, including the vector column on knowledge_items.
- Unit tests are created for the domain models, and integration tests are created for the repositories.

## Story 2.2: LLM & Embedding Provider Factory
As a AI Agent Developer, I want a flexible, pluggable factory for LLM and embedding providers, so that I am not locked into a single provider and can support local models (NFR8).

### Acceptance Criteria:
- An abstract ILLMProvider interface is defined, specifying methods like embed_text(...) and generate_completion(...).
- Concrete implementations of the interface are created for OpenAIProvider, AnthropicProvider, OllamaProvider, and OpenRouterProvider (NFR8).
- A ProviderFactory is created that reads the LLM_PROVIDER and EMBEDDING_PROVIDER from settings.py and returns the correct provider instance.
- The factory is integrated into the FastAPI app's dependency injection system.
- Configuration in .env.example is updated to include API keys and model names for all supported providers.

## Story 2.3: Document Management API (CRUD)
As a AI Agent Developer, I want to perform full CRUD and versioning operations on Documents via the secured REST API, so that I can manage my project's knowledge sources.

### Acceptance Criteria:
- All endpoints are protected by the JWT authentication dependency (from Story 1.4).
- POST `/api/v1/documents`: Creates a new document (v1.0.0) linked to a project.
- GET `/api/v1/documents`: Lists all documents for a given project, with pagination.
- GET `/api/v1/documents/{id}`: Retrieves a specific document (defaults to latest version). Can query for a specific version.
- PUT `/api/v1/documents/{id}`: Updates the metadata (e.g., name, tags) of a document.
- DELETE `/api/v1/documents/{id}`: Deletes a document.
- POST `/api/v1/documents/{id}/version`: Creates a new version of an existing document (e.g., v1.0.1) (FR3).
- E2E tests are created for all endpoints, verifying functionality, auth, and validation.

## Story 2.4: Task Management API (CRUD)
As a AI Agent Developer, I want to perform full CRUD operations on Tasks via the secured REST API, so that I can track work within my projects.

### Acceptance Criteria:
- All endpoints are protected by the JWT authentication dependency.
- POST `/api/v1/tasks`: Creates a new task linked to a project (FR5).
- GET `/api/v1/tasks`: Lists all tasks for a given project, with filtering by status or assignee.
- GET `/api/v1/tasks/{id}`: Retrieves a single task by its ID.
- PUT `/api/v1/tasks/{id}`: Updates a task (e.g., status, priority, assignee) (FR5).
- DELETE `/api/v1/tasks/{id}`: Deletes a task.
- E2E tests are created for all endpoints.

## Story 2.5: Knowledge Ingestion - File Upload Pipeline
As a AI Agent Developer, I want to upload a file (MD, PDF, DOCX, HTML) to an endpoint, so that it is automatically processed, chunked, embedded, and stored as KnowledgeItems.

### Acceptance Criteria:
- A new endpoint POST `/api/v1/knowledge/upload` is created that accepts a file upload (FR6).
- The endpoint creates a new Document (using logic from 2.3) to represent the file.
- The system correctly extracts text content from the supported file types (MD, PDF, DOCX, HTML) (FR4).
- The extracted text is passed to a text chunker (e.g., semantic chunking).
- The text chunks are passed to the embedding provider (from Story 2.2) to get vectors.
- Each chunk, its vector, and metadata are saved as a new KnowledgeItem in the database, linked to the Document (FR8).
- This process is asynchronous (e.g., using FastAPI's BackgroundTasks) to avoid blocking the API response.

## Story 2.6: Knowledge Ingestion - Web Crawl Pipeline
As a AI Agent Developer, I want to submit a URL to an endpoint, so that the web page is automatically crawled, processed, embedded, and stored as KnowledgeItems.

### Acceptance Criteria:
- A new endpoint POST `/api/v1/knowledge/crawl` is created that accepts a URL and a project ID (FR7).
- A web crawling service (e.g., using httpx and BeautifulSoup) is created to fetch and parse the HTML content from the URL.
- The endpoint creates a new Document (using logic from 2.3) to represent the crawled page.
- The extracted text is processed, chunked, embedded, and stored as KnowledgeItems, following the same pipeline as Story 2.5 (FR8).
- This process is asynchronous (BackgroundTasks).
- The crawler respects robots.txt (or has an option to ignore it).
