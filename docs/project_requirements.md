# Contextiva Product Requirements Document (PRD)

## Goals and Background Context

### Goals
The primary goals for this PRD are to:
        - Deliver a production-ready, reliable, and secure knowledge engine service.
        - Drive developer adoption by providing a service that saves significant infrastructure and development time.
        - Ensure the architecture is extensible and pluggable to support multiple LLM providers and data sources.
        - Provide a highly relevant and accurate RAG system for AI agents.

## Background Context
The current generation of AI agents often operates statelessly, lacking a persistent, contextual "memory". This forces developers to repeatedly build bespoke, in-house knowledge systems, a significant engineering effort that detracts from building the agent's core intelligence. Existing solutions are often just libraries (like LangChain) that leave the infrastructure burden (database, API, security) on the user, or simple vector stores that lack the rich domain logic for managing projects and versioned documents.

Contextiva solves this by providing a standalone, production-ready knowledge engine built on Clean Architecture and Domain-Driven Design (DDD). It abstracts the entire knowledge infrastructure stack (FastAPI, PostgreSQL/pgvector, Redis) into a clean REST API and Model Context Protocol (MCP) service. This allows developers to stop rebuilding infrastructure and instead focus on building their agent's unique intelligence by consuming a ready-to-deploy "knowledge-as-a-service" backend.

## Requirements

### Functional
- **FR1 (Project Management)**: The system MUST support full CRUD operations for Projects, including hierarchical organization, status management (Active, Archived), and tag-based organization.
- **FR2 (Project Integration)**: The system MUST support integration with GitHub repositories as a knowledge source for a project.
- **FR3 (Document Management)**: The system MUST support full CRUD operations for Documents within a project, including semantic version control.
- **FR4 (Document Ingestion)**: The system MUST support the ingestion of multiple document formats, including Markdown, PDF, DOCX, and HTML.
- **FR5 (Task Management)**: The system MUST support project-scoped CRUD operations for Tasks, including tracking priority, status, assignees, and dependencies.
- **FR6 (RAG Ingestion - Upload)**: The system MUST provide an endpoint (/api/v1/knowledge/upload) for ingesting knowledge via file upload.
- **FR7 (RAG Ingestion - Crawl)**: The system MUST provide an endpoint (/api/v1/knowledge/crawl) for ingesting knowledge from a specified URL.
- **FR8 (RAG Processing)**: The system MUST automatically extract, chunk, and create embeddings for all ingested documents (text, code, structured data).
- **FR9 (RAG Retrieval)**: The system MUST provide an endpoint (/api/v1/rag/query) for knowledge retrieval, supporting semantic search.
- **FR10 (RAG Advanced Retrieval)**: The RAG retrieval system MUST also support Hybrid Search, contextual embeddings, re-ranking, and agentic RAG capabilities.
- **FR11 (API - REST)**: The system MUST expose all core functionalities (Projects, Documents, Tasks, RAG) via a clean, versioned REST API (FastAPI).
- **FR12 (API - MCP)**: The system MUST provide a functional Model Context Protocol (MCP) server for native AI agent integration.

## Non-Functional
- **NFR1 (Architecture)**: The system MUST be built following Clean Architecture and Domain-Driven Design (DDD) principles, with a clear separation of API, Application, Domain, and Infrastructure layers.
- **NFR2 (Security - Auth)**: The system MUST support JWT tokens for authenticating API requests and implement Role-Based Access Control (RBAC).
- **NFR3 (Security - API)**: The system MUST implement Rate Limiting, CORS policies, and use Pydantic for all input validation to protect against common web vulnerabilities.
- **NFR4 (Security - Data)**: The system MUST protect against SQL Injection via the use of parameterized queries and the repository pattern.
- **NFR5 (Performance - Async)**: The system MUST be built using FastAPI and leverage async/await for all non-blocking I/O operations to ensure high throughput.
- **NFR6 (Performance - Caching)**: The system MUST use Redis for caching frequently repeated queries.
- **NFR7 (Performance - Throughput)**: The system MUST be optimized to handle target benchmarks (e.g., 2000 req/s for reads, 100 req/s for search) and use batch processing for bulk operations.
- **NFR8 (Extensibility)**: The system MUST use a Factory Pattern for LLM and embedding services to allow for pluggable support, minimally including OpenAI, Anthropic, Ollama, and OpenRouter.
- **NFR9 (Observability)**: The system MUST provide Structured Logging (JSON), Request Tracing, Error Tracking, and Health Check endpoints.
- **NFR10 (Deployment)**: The system MUST be fully containerized and deployable via the provided docker-compose.yml and include k8s/ configurations.
- **NFR11 (Database)**: The system MUST use a PostgreSQL-compatible database with the pgvector extension.

## Technical Assumptions
These technical decisions are derived from the Project Brief and serve as hard constraints for the architecture.

### Repository Structure: Monorepo
- A monorepo structure will be used.
- **Rationale**: This approach is ideal for a Clean Architecture, allowing for clear separation of concerns (e.g., src/api, src/application, src/domain, src/infrastructure) and easier management of shared code, such as domain models and DTOs, within a single repository.

### Service Architecture: Monolith (Clean Architecture)
- The service will be built as a single deployable unit (a monolith) following Clean Architecture and Domain-Driven Design (DDD) principles.
- **Rationale**: This provides a robust, maintainable, and testable codebase. While the "Roadmap" (v3.0) envisions a microservices architecture, the v2.0 MVP is a monolith, which is simpler to build and deploy initially.

### Testing Requirements: Full Testing Pyramid
- The project will require a comprehensive testing strategy:
- **Unit Tests (pytest)**: For domain logic and use cases.
- **Integration Tests (pytest)**: For the infrastructure layer (e.g., repository pattern against a test database).
- **E2E Tests (pytest)**: For the API endpoints.
- **Rationale**: The goal of a "production-ready" engine (NFR1) necessitates a high degree of reliability, which can only be achieved with a full testing pyramid.

### Additional Technical Assumptions and Requests
- **Language/Framework**: Python 3.11+ and FastAPI are mandatory.
- **Database**: PostgreSQL with pgvector extension (or Supabase) is mandatory.
- **Cache**: Redis is a required component for performance.
- **Security**: The full security stack (JWT, RBAC, Pydantic Validation, Rate Limiting, CORS) is a non-negotiable requirement.
- **API**: The system must expose both a REST API and an MCP Server.

## Epic List

### Epic 1: Foundation & Core Services (Project Management)
**Goal**: Establish the full production-ready application foundation—including the Clean Architecture, database (pgvector), deployment (Docker), security (JWT/RBAC stubs), and logging—while delivering the core Project Management API endpoints.

### Epic 2: Knowledge Ingestion & Lifecycle (Document & Task Management)
**Goal**: Build on the "Project" foundation to implement the complete Document and Task management systems, and deliver the full knowledge ingestion pipeline (file/web upload, chunking, and embedding).

### Epic 3: Advanced RAG Retrieval & Agent Integration
**Goal**: Expose the advanced RAG query engine (semantic/hybrid search, re-ranking, agentic RAG) and deliver the complete, agent-facing REST API and Model Context Protocol (MCP) server for final consumption.


## Epic 1: Foundation & Core Services (Project Management)
**Epic Goal**: Establish the full production-ready application foundation—including the Clean Architecture, database (pgvector), deployment (Docker), security (JWT/RBAC stubs), and logging—while delivering the core, secured Project Management API endpoints. This epic delivers the complete, testable "scaffolding" and the first piece of core domain value.

### Story 1.1: Project Foundation & Scaffolding
As a AI Agent Developer, I want a new project repository initialized with the complete Clean Architecture directory structure and core dependencies, so that I can immediately start development following DDD principles.

#### Acceptance Criteria:
- A pyproject.toml file is created, managed by poetry, with Python 3.11+ specified.
- Core dependencies are added: fastapi, pydantic, uvicorn, asyncpg (for Supabase/PostgreSQL), redis, python-jose[cryptography] (for JWT), and passlib[bcrypt] (for auth).
- The complete Clean Architecture directory structure is scaffolded (e.g., src/api, src/application, src/domain, src/infrastructure, src/shared).
- Basic alembic migration setup is created in a migration/ folder.
- Base configuration files are created: README.md, .env.example, .gitignore, and a docker-compose.yml (defining api, postgres, and redis services).
- `src/api/main.py` is created with a basic FastAPI app instance and a `/api/docs` (Swagger) endpoint.
- A health check endpoint (GET `/api/v1/health`) is implemented and returns a 200 OK status.

### Story 1.2: Database & Observability Integration
As a AI Agent Developer, I want the FastAPI application to be fully connected to the PostgreSQL/pgvector database and a structured logging system, so that the application is ready for persistence and observability.

#### Acceptance Criteria:
- A `src/shared/config/settings.py` module is created to load all database and logging settings from environment variables.
- A database connection module (e.g., `src/shared/infrastructure/database/connection.py`) is created and manages the connection pool.
- An Alembic migration is created and run to enable the pgvector extension in the database.
- A structured logging module (`src/shared/config/logging.py`) is created and integrated into the FastAPI app to output JSON-formatted logs (NFR9).
- A middleware is added to log all incoming API requests with a unique request ID (NFR9).
The health check endpoint (GET `/api/v1/health`) is updated to successfully verify database connectivity.

### Story 1.3: Core Domain Model (Project) & Repository
As a AI Agent Developer, I want the Project domain model, repository interface, and concrete implementation defined, so that I can build business logic independent of the database.

#### Acceptance Criteria:
- The Project entity is defined in src/domain/models/project.py with core attributes (id, name, description, status, tags) and business rules (NFR1).
- The IProjectRepository abstract base class (interface) is defined in src/domain/models/project.py.
- The concrete ProjectRepository implementation is created in src/infrastructure/database/repositories/project_repository.py, implementing the interface.
- Unit tests for the Project domain model's business logic (if any) are created.
- Integration tests for the ProjectRepository are created, verifying all CRUD operations against a test database.

### Story 1.4: Security & Auth Foundation
As a AI Agent Developer, I want a basic JWT token creation and validation system in place, so that I can secure all future API endpoints.

#### Acceptance Criteria:
- A security utility module is created to handle JWT token creation (e.g., create_access_token) and decoding/validation (NFR2).
- A basic User domain model (with hashed_password) and UserRepository are created (following the pattern from 1.3).
- A simple POST /api/v1/auth/token endpoint is created that accepts a username/password (for testing) and returns a valid JWT.
- A FastAPI dependency (get_current_user) is created to protect endpoints, which validates the JWT and returns the user model.
- Stub files/classes for Role-Based Access Control (RBAC) are created (e.g., in src/api/dependencies.py), but the complex logic is deferred (NFR2).

### Story 1.5: Project Management API (CRUD)
As a AI Agent Developer, I want to perform full CRUD operations on Projects via the secured REST API, so that I can manage my agent's knowledge projects.

#### Acceptance Criteria:
- All Project API endpoints (except OPTIONS) are protected by the JWT authentication dependency from Story 1.4 (AC 1.4).
- POST `/api/v1/projects`: Creates a new project, validates input using a Pydantic schema, and returns the created project.
- GET `/api/v1/projects`: Lists all projects for the authenticated user, supporting pagination.
- GET `/api/v1/projects/{id}`: Retrieves a single project by its ID, ensuring the user has access.
- PUT `/api/v1/projects/{id}`: Updates an existing project, validating input and access.
- DELETE `/api/v1/projects/{id}`: Deletes an existing project, ensuring the user has access.
- E2E tests are created for all 5 endpoints, verifying functionality, authentication, authorization (basic access), and Pydantic validation error handling.

## Epic 2: Knowledge Ingestion & Lifecycle (Document & Task Management)
**Epic Goal**: Build on the "Project" foundation to implement the complete Document and Task management systems, and deliver the full knowledge ingestion pipeline. This includes setting up the flexible LLM/Embedding provider factory and implementing both file and web-based ingestion, processing (chunking/embedding), and storage.

### Story 2.1: Core Domain Models (Document, Task, KnowledgeItem)
As a AI Agent Developer, I want the Document, Task, and KnowledgeItem domain models and repositories defined, so that I can build the core ingestion and tracking logic.

#### Acceptance Criteria:
- The Document entity is defined in src/domain/models/document.py, including attributes for project_id, name, type, version, and content_hash. It must support semantic versioning (NFR1, FR3).
- The Task entity is defined in src/domain/models/task.py, including attributes for project_id, title, status, priority, assignee, and dependencies (NFR1, FR5).
- The KnowledgeItem entity is defined in src/domain/models/knowledge.py, including document_id, chunk_text, embedding (using pgvector's Vector type), and metadata.
- Respective repository interfaces (IDocumentRepository, ITaskRepository, IKnowledgeRepository) and concrete PostgreSQL implementations are created (NFR1).
- Alembic migrations are created to establish the new documents, tasks, and knowledge_items tables, including the vector column on knowledge_items.
- Unit tests are created for the domain models, and integration tests are created for the repositories.

### Story 2.2: LLM & Embedding Provider Factory
As a AI Agent Developer, I want a flexible, pluggable factory for LLM and embedding providers, so that I am not locked into a single provider and can support local models (NFR8).

#### Acceptance Criteria:
- An abstract ILLMProvider interface is defined, specifying methods like embed_text(...) and generate_completion(...).
- Concrete implementations of the interface are created for OpenAIProvider, AnthropicProvider, OllamaProvider, and OpenRouterProvider (NFR8).
- A ProviderFactory is created that reads the LLM_PROVIDER and EMBEDDING_PROVIDER from settings.py and returns the correct provider instance.
- The factory is integrated into the FastAPI app's dependency injection system.
- Configuration in .env.example is updated to include API keys and model names for all supported providers.

### Story 2.3: Document Management API (CRUD)
As a AI Agent Developer, I want to perform full CRUD and versioning operations on Documents via the secured REST API, so that I can manage my project's knowledge sources.

#### Acceptance Criteria:
- All endpoints are protected by the JWT authentication dependency (from Story 1.4).
- POST /api/v1/documents: Creates a new document (v1.0.0) linked to a project.
- GET /api/v1/documents: Lists all documents for a given project, with pagination.
- GET /api/v1/documents/{id}: Retrieves a specific document (defaults to latest version). Can query for a specific version.
- PUT /api/v1/documents/{id}: Updates the metadata (e.g., name, tags) of a document.
- DELETE /api/v1/documents/{id}: Deletes a document.
- POST /api/v1/documents/{id}/version: Creates a new version of an existing document (e.g., v1.0.1) (FR3).
- E2E tests are created for all endpoints, verifying functionality, auth, and validation.

### Story 2.4: Task Management API (CRUD)
As a AI Agent Developer, I want to perform full CRUD operations on Tasks via the secured REST API, so that I can track work within my projects.

#### Acceptance Criteria:
- All endpoints are protected by the JWT authentication dependency.
- POST /api/v1/tasks: Creates a new task linked to a project (FR5).
- GET /api/v1/tasks: Lists all tasks for a given project, with filtering by status or assignee.
- GET /api/v1/tasks/{id}: Retrieves a single task by its ID.
- PUT /api/v1/tasks/{id}: Updates a task (e.g., status, priority, assignee) (FR5).
- DELETE /api/v1/tasks/{id}: Deletes a task.
- E2E tests are created for all endpoints.

### Story 2.5: Knowledge Ingestion - File Upload Pipeline
As a AI Agent Developer, I want to upload a file (MD, PDF, DOCX, HTML) to an endpoint, so that it is automatically processed, chunked, embedded, and stored as KnowledgeItems.

#### Acceptance Criteria:
- A new endpoint POST /api/v1/knowledge/upload is created that accepts a file upload (FR6).
- The endpoint creates a new Document (using logic from 2.3) to represent the file.
- The system correctly extracts text content from the supported file types (MD, PDF, DOCX, HTML) (FR4).
- The extracted text is passed to a text chunker (e.g., semantic chunking).
- The text chunks are passed to the embedding provider (from Story 2.2) to get vectors.
- Each chunk, its vector, and metadata are saved as a new KnowledgeItem in the database, linked to the Document (FR8).
- This process is asynchronous (e.g., using FastAPI's BackgroundTasks) to avoid blocking the API response.

### Story 2.6: Knowledge Ingestion - Web Crawl Pipeline
As a AI Agent Developer, I want to submit a URL to an endpoint, so that the web page is automatically crawled, processed, embedded, and stored as KnowledgeItems.

#### Acceptance Criteria:
- A new endpoint POST /api/v1/knowledge/crawl is created that accepts a URL and a project ID (FR7).
- A web crawling service (e.g., using httpx and BeautifulSoup) is created to fetch and parse the HTML content from the URL.
- The endpoint creates a new Document (using logic from 2.3) to represent the crawled page.
- The extracted text is processed, chunked, embedded, and stored as KnowledgeItems, following the same pipeline as Story 2.5 (FR8).
- This process is asynchronous (BackgroundTasks).
- The crawler respects robots.txt (or has an option to ignore it).

## Epic 3: Advanced RAG Retrieval & Agent Integration
**Epic Goal**: Expose the knowledge ingested in Epic 2 by building the complete, agent-facing query pipeline. This includes the core semantic search API, the advanced RAG features (hybrid search, re-ranking, synthesis), and the Model Context Protocol (MCP) server for native agent integration.

### Story 3.1: RAG Retrieval API (Core Query)
As a AI Agent Developer, I want a secured API endpoint to send a text query, so that I can receive the most relevant KnowledgeItems from my project.

#### Acceptance Criteria:
- A new endpoint POST /api/v1/rag/query is created and secured using the JWT authentication dependency (from Story 1.4).
- The endpoint accepts a Pydantic schema containing at least project_id and query_text.
- The incoming query_text is converted to an embedding using the configured Embedding Provider (from Story 2.2).
- The system performs a vector similarity search (using pgvector) against KnowledgeItems that match the project_id.
- The search MUST return the top-K (e.g., K=5, configurable via settings.py) matching KnowledgeItem chunks.
- E2E tests are created to ingest a document (using the API from Story 2.5) and then successfully query for its content.

### Story 3.2: Advanced RAG - Hybrid Search & Re-ranking
As a AI Agent Developer, I want the RAG query endpoint to optionally support Hybrid Search and Re-ranking, so that I can improve the relevance of my search results (FR10).

#### Acceptance Criteria:
- The POST /api/v1/rag/query endpoint is updated to accept optional boolean flags: use_hybrid_search and use_re_ranking.
- If use_hybrid_search is true, the system performs both vector search (from 3.1) and traditional keyword search (e.g., BM25/full-text search) and merges the results.
- If use_re_ranking is true, the initial set of retrieved chunks (from AC 3.1.5 or 3.2.2) is passed to an LLM provider (from Story 2.2) to re-rank them for relevance to the original query.
- Configuration in settings.py is added to enable/disable these features by default (e.g., RAG_USE_HYBRID_SEARCH=false, RAG_USE_RERANKING=false).
- E2E tests are updated to validate the behavior when these flags are enabled and disabled.

### Story 3.3: Advanced RAG - Agentic RAG (Synthesis)
As a AI Agent Developer, I want the RAG query endpoint to optionally return a synthesized, natural language answer, so that my agent can consume a direct response instead of just raw chunks (FR10).

#### Acceptance Criteria:
- The POST /api/v1/rag/query endpoint is updated to accept an optional boolean flag: use_agentic_rag.
- If use_agentic_rag is true, the system takes the final (re-ranked) chunks, along with the original query, and passes them to an LLM provider (from Story 2.2) with a "summarize" or "answer based on context" prompt.
- The API response is updated to include a new optional field, synthesized_answer, containing the LLM's natural language response.
- Configuration in settings.py is added to enable/disable this feature by default (RAG_USE_AGENTIC=false).
- E2E tests are updated to validate that a synthesized answer is correctly returned when the flag is enabled.

### Story 3.4: MCP Server Integration
As a an AI Agent (programmatic client), I want to connect to a Model Context Protocol (MCP) server, so that I can natively interact with the Contextiva knowledge engine (FR12).

#### Acceptance Criteria:
- An mcp/server.py file is created that implements the MCP specification, as defined in the project structure.
- The MCP server is configured as a new service (mcp) in the docker-compose.yml file.
- The MCP server re-uses the application services (e.g., ProjectService, RAGService) to fulfill agent requests.
- MCP tools are defined for core agent actions: create_project, ingest_document, and query_knowledge.
- The MCP server is secured using the same JWT authentication logic as the REST API.
- E2E tests are created to connect to the MCP server (e.g., via a simple client) and execute a basic query_knowledge tool call.

