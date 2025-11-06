# MVP Scope
This MVP scope is defined by the features listed in the Contextiva README for the current version (v2.0). It represents a complete, production-ready knowledge engine. Features explicitly listed on the roadmap (v2.1+) are considered out of scope for this initial build.

## Core Features (Must Have)
- **Project Management**: Full CRUD operations for Projects, including hierarchical organization, GitHub integration, status management (Active, Archived), and tag-based organization.
- **Document Management**: Full CRUD and version control for Documents (PRD, API, Specs, etc.). Must support ingestion of Markdown, PDF, DOCX, and HTML.
- **Task Management**: Project-scoped Task tracking with support for priority, status, assignees, and d dependencies.
- **Advanced RAG System**: A complete RAG pipeline including:
        - **Ingestion**: File upload (/knowledge/upload) and web crawling (/knowledge/crawl).
        - **Processing**: Automatic extraction, chunking, and embedding.
        - **Retrieval**: Semantic search, Hybrid Search, Contextual Embeddings, Re-ranking, and Agentic RAG.
        - **Support**: Must handle text, code, and structured data.
- **LLM Integration Factory**: A flexible, pluggable system to support multiple providers, minimally including OpenAI, Anthropic, Ollama, and OpenRouter.
- **Production-Grade API**:
        - **REST API (FastAPI)**: A clean API with all documented endpoints for Projects, Documents, Tasks, and RAG Search.
        - **MCP Integration**: A functional Model Context Protocol (MCP) server for native agent integration.
- **Technical Foundation**:
        - **Architecture**: Built on Clean Architecture and Domain-Driven Design principles.
        - **Performance**: Must include Async/Await operations, Redis Caching, and Batch Processing.
        - **Security**: Must implement JWT token support, Role-Based Access Control (RBAC), Pydantic validation, Rate Limiting, and CORS.
        - **Observability**: Must include Structured Logging, Request Tracing, Error Tracking, and Health Check endpoints.
- **Deployment**: Must be fully deployable via the provided docker-compose.yml and include Kubernetes (k8s/) configurations.

## Out of Scope for MVP
This list is based on the v2.1, v2.2, and v3.0 "Roadmap" items:
- GraphQL API
- Real-time updates (WebSocket)
- Advanced analytics dashboard
- Multi-tenant support
- Event sourcing implementation
- CQRS pattern
- Distributed tracing
- Full Microservices architecture
- Service mesh integration
- Multi-modal RAG for images or audio
- Agent marketplace

## MVP Success Criteria
The MVP will be considered successful when:

1. A developer can successfully clone the repository, configure the .env file, and launch the entire stack (API, database, cache) using a single docker-compose up -d command.
2. A user (or test script) can hit the REST API to:
        - POST /api/v1/projects to create a new project.
        - POST /api/v1/knowledge/upload to upload a document to that project.
        - POST /api/v1/knowledge/crawl to crawl a public URL for that project.
        - POST /api/v1/rag/query and receive a relevant, context-aware answer from the ingested documents.
3. All API endpoints are verifiably protected by the security layer (e.g., returning a 401/403 error without a valid JWT token).
4. The system demonstrates baseline performance: health checks are responsive, and cached queries return significantly faster than non-cached ones.
5. The LLM Integration factory can be successfully configured to use at least two different providers (e.g., OpenAI and a local Ollama instance).
