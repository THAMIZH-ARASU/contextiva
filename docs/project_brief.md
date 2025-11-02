# Contextiva Project Brief Document

## Executive Summary
Contextiva is a modern, production-ready knowledge engine designed specifically to empower AI agents with contextual knowledge. The primary problem it solves is the lack of a persistent, intelligent, and accessible knowledge store for AI systems, enabling them to move beyond simple stateless tasks.

The solution is a standalone service built on Clean Architecture and Domain-Driven Design (DDD) principles. It provides a comprehensive suite of features through a clean REST API and Model Context Protocol (MCP) integration.

### Key capabilities include:
- Hierarchical Project and Task Management.
- Version-controlled Document Management (PRDs, Arch docs, etc.).
- An Advanced RAG System featuring semantic/hybrid search, re-ranking, and agentic RAG.
- Web Crawling for knowledge ingestion.
- A Flexible LLM Integration factory supporting providers like OpenAI, Anthropic, and local Ollama instances.

The target market is AI agent developers who need a robust, scalable, and secure knowledge backend. The key value proposition is providing this production-grade engine—built on FastAPI, PostgreSQL (pgvector), and Redis—as a ready-to-deploy service, abstracting away the complex infrastructure and domain logic.

## Problem Statement
The current generation of AI agents, while powerful in execution, fundamentally lacks a persistent, contextual "memory." Developers are forced to build bespoke, in-house knowledge systems for each agent, often mixing knowledge management logic directly with agent orchestration code.

### Current State & Pain Points:
- **Stateless Agents**: Most agents operate on a per-request basis, unable to reference past interactions, manage complex projects, or build a cumulative knowledge base over time.
- **Infrastructure Burden**: Developers must manually provision, configure, and scale vector databases, API servers, caching layers, and ingestion pipelines—a significant engineering effort that detracts from building the agent's core intelligence.
- **Lack of Versioning**: Technical and project documentation (PRDs, specs) evolves. Agents often retrieve outdated information because existing solutions lack robust document version control.
- **Inefficient Retrieval**: Simple vector search is often not enough. Agents require advanced RAG (Retrieval-Augmented Generation) with hybrid search, re-ranking, and contextual understanding to get relevant, accurate information.

### Why Existing Solutions Fall Short:
- Orchestration Frameworks: Tools like LangChain provide "concepts" and "orchestration"  but are not persistent, standalone services. They are the "glue" that can call an engine like Contextiva, but they leave the burden of data persistence, API creation, and infrastructure management on the user.
- Monolithic Vector Databases: While excellent at vector search, they are not complete knowledge engines. They lack the domain-specific logic for managing hierarchical projects, tracking tasks, versioning documents, or providing a clean REST API tailored for agent workflows.

The impact is a proliferation of brittle, hard-to-maintain, and non-scalable agent architectures. The urgency is driven by the rapid shift towards more complex, autonomous agents that are expected to perform sophisticated, long-running tasks. Without a production-ready knowledge engine, agent capabilities will hit a hard ceiling.

## Proposed Solution
The proposed solution is Contextiva, a standalone, production-ready knowledge engine, designed from the ground up to serve as the persistent "brain" for AI agents. It addresses the problem by abstracting the entire knowledge infrastructure stack into a clean, robust, and scalable service.
Core Concept and Approach: Contextiva is built using Clean Architecture and Domain-Driven Design (DDD), ensuring a clear separation of concerns between the core domain logic (Projects, Documents, Tasks), the application use cases (Ingest, Search), and the infrastructure (database, LLM providers).

The engine will provide:
1. **A Clean REST API**: A set of well-defined endpoints (e.g., /projects, /documents, /rag/query) for any AI agent or client to interact with.
2. **Model Context Protocol (MCP) Integration**: A seamless, native connection point for agents designed to use MCP.
3. **Advanced RAG System**: A retrieval-augmented generation (RAG) system that goes beyond simple vector search to include hybrid search, re-ranking, and agentic RAG for synthesized, contextual answers.
4. **Flexible Knowledge Ingestion**: Capabilities to ingest knowledge from multiple sources, including file uploads (Markdown, PDF, DOCX) and automated web crawling.

### Key Differentiators:
- **Production-Ready Infrastructure**: Unlike a simple library, Contextiva is a complete service. It is built with a high-performance stack (FastAPI, PostgreSQL + pgvector, Redis caching) and designed for scalability and security (JWT, rate limiting, connection pooling).
- **Rich Domain Model**: It's not just a vector store. It understands the domain of AI development, with rich models for Projects (hierarchical), Documents (version-controlled), and Tasks (trackable).
- **Pluggable Architecture**: The system is not locked into any single provider. It features a factory pattern for LLM and embedding services, supporting OpenAI, Anthropic, Ollama, and OpenRouter out-of-the-box.

This solution will succeed by providing a battle-tested, off-the-shelf "knowledge-as-a-service" backend. This allows developers to stop rebuilding a complex, non-trivial infrastructure stack for every project and instead focus on building their agent's unique intelligence.

## Target Users

### Primary User Segment: AI Agent Developer / ML Engineer
- **Profile**: These are Python developers, ML engineers, or backend teams responsible for building, deploying, and maintaining applications that leverage Large Language Models (LLMs) and autonomous agents.
- **Current Behaviors**: They are currently writing significant amounts of boilerplate code to connect agents to vector stores, manage document ingestion pipelines (chunking, embedding), and build custom APIs for knowledge retrieval. They often find themselves managing this complex infrastructure instead of focusing on their agent's core logic.
- **Specific Needs & Pain Points**:
        - They suffer from the "infrastructure burden" of provisioning and scaling databases (like pgvector), caching layers (like Redis), and API servers.
        - They need a service, not just a library, that is production-ready with built-in security (JWT, RBAC), performance (async, connection pooling), and observability.
        - They require a solution that understands the domain of AI development, including versioning for technical documents (PRDs, specs) and hierarchical project management.

- **Goals**: To accelerate the development and deployment of sophisticated, knowledgeable, and reliable AI agents by integrating a pre-built, production-grade knowledge engine.

### Secondary User Segment: AI Agent (Programmatic Client)
- **Profile**: An autonomous software program (e.g., a BMad agent, a custom-built agent) that needs to programmatically access external knowledge to perform complex tasks.
- **Current Behaviors**: The agent often operates statelessly or relies on simple, in-memory vector stores. It lacks long-term, persistent memory and the context of a "project."
- **Specific Needs & Pain Points**:
        - Cannot manage complex, multi-step projects that require cumulative knowledge.
        - Retrieves irrelevant or outdated information because the underlying knowledge base lacks document versioning or advanced retrieval strategies.

- **Goals**: To query a persistent, version-controlled knowledge base via a clean API (REST or MCP) to retrieve highly relevant, contextual information on demand. This enables the agent to complete tasks more accurately, effectively, and with a consistent "memory."

## Goals & Success Metrics

### Business Objectives
- **Establish Production Readiness**: Provide a highly reliable, scalable, and secure service, moving beyond a library/framework to a full-fledged engine.
- **Drive Developer Adoption**: Become the go-to, off-the-shelf knowledge backend for AI agent developers, saving them significant infrastructure and development time.
- **Ensure Extensibility**: Create a flexible, pluggable architecture that supports a wide array of current and future LLM providers and data sources.

### User Success Metrics
- **For the AI Agent Developer (Primary User)**:
        - Reduced time-to-deployment for new, knowledgeable AI agents.
        - High developer satisfaction with API clarity, documentation, and ease of integration.
        - Low overhead in managing, scaling, or maintaining the knowledge infrastructure.
-  **For the AI Agent (Secondary User)**:
        - High relevance and accuracy of retrieved context (measured by RAG re-ranking and similarity scores).
        - Low-latency responses for semantic queries.
        - Successful and consistent interaction with version-controlled documents.

### Key Performance Indicators (KPIs)
- **API Performance**:
        - P95 Latency for POST /api/v1/rag/query (e.g., < 250ms).
        - API Request Throughput (e.g., 500+ req/s for core read operations).
        - API Error Rate (e.g., < 0.1%).
- **RAG System**:
        - Document Ingestion Throughput (e.g., 50 req/s).
        - RAG Similarity Threshold (RAG_SIMILARITY_THRESHOLD).
        - Effectiveness of Hybrid Search and Re-ranking (if enabled).
- **Adoption & Usage**:
        - Number of active Projects created.
        - Total number of Documents ingested and versioned.
        - Volume of API calls to core endpoints (query, ingest, task updates).
- **Extensibility**:
        - Number of LLM providers supported (currently supports OpenAI, Anthropic, Ollama, OpenRouter).

## MVP Scope
This MVP scope is defined by the features listed in the Contextiva README for the current version (v2.0). It represents a complete, production-ready knowledge engine. Features explicitly listed on the roadmap (v2.1+) are considered out of scope for this initial build.

### Core Features (Must Have)
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

### Out of Scope for MVP
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

### MVP Success Criteria
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

## Post MVP Vision
The Post-MVP vision for Contextiva is to evolve from a production-ready knowledge engine into a comprehensive, multi-modal, and decentralized ecosystem for agentic knowledge. This is structured in a clear, phased roadmap.

### Phase 2 Features (Roadmap v2.1 - Q1 2025)
- **GraphQL API**: Offer a GraphQL API as an alternative to REST for more flexible client-side data queries.
- Real-time Updates (WebSocket): Enable real-time notifications for changes in tasks, documents, or project status.
- **Advanced Analytics Dashboard**: Provide a visual dashboard for administrators to monitor system usage, query performance, and knowledge base health.
- **Multi-tenant Support**: Introduce full multi-tenancy to securely isolate data and operations between different organizations or users.

### Long-term Vision (Roadmap v2.2 - Q2 2025)
- **Advanced Architectural Patterns**: Implement Event Sourcing and the CQRS (Command Query Responsibility Segregation) pattern to create a fully auditable and even more scalable system.
- **Enhanced Observability**: Integrate distributed tracing to provide a complete, end-to-end view of requests as they flow through the system.
- **Advanced RAG Strategies**: Continue to innovate on the RAG system with new retrieval and synthesis techniques.

### Expansion Opportunities (Roadmap v3.0 - Q3 2025)
- **Microservices Architecture**: Decompose the monolith into a true microservices architecture to allow for independent scaling and development of components.
- **Service Mesh Integration**: Implement a service mesh for managing inter-service communication, security, and observability.
- **Multi-modal RAG**: Expand the RAG system to ingest, index, and query against images and audio, not just text.
- **Agent Marketplace**: Create a marketplace where developers can share and discover agents that are pre-configured to use the Contextiva engine.

## Technical Considerations
These considerations are not preferences but are the defined, core architecture of the Contextiva engine as documented.

### Platform Requirements
- **Target Platforms**: This is a containerized backend service designed for cloud deployment. The primary interfaces are a REST API and an MCP Server.
- **Performance Requirements**: The system is built for high-performance, non-blocking I/O. Benchmarks target high throughput (e.g., 2000 req/s for reads, 100 req/s for semantic search) and low latency (e.g., 15ms p95 for reads).

### Technology Preferences
- **Backend**: Python 3.11+ , FastAPI.
- **Database**: Supabase, or any PostgreSQL with the pgvector extension.
- **Cache**: Redis (optional but recommended for performance).
- **Package Management**: Poetry.
- **Hosting/Infrastructure**: The system is designed for containerized deployment via Docker, Docker Compose, and Kubernetes.

### Architecture Considerations
- **Repository Structure**: A monorepo structure containing the core src/, migration/, tests/, etc.
- **Service Architecture**: A strict Clean Architecture and Domain-Driven Design (DDD)  approach is used. This separates concerns into API, Application, Domain, and Infrastructure layers.
- **Integration Requirements**:
        - Exposes a REST API (FastAPI) and an MCP Server for agent integration.
        - Features a pluggable LLM Integration factory supporting OpenAI, Anthropic, Ollama, and OpenRouter.
        - Uses the Repository Pattern for data access abstraction.
- **Security/Compliance**: The architecture mandates a production-ready security model, including JWT token support, Role-Based Access Control (RBAC), Pydantic schema validation, SQL Injection Protection, Rate Limiting, and CORS policies.

## Constraints & Assumptions

### Constraints
- **Timeline**: Not specified. (This brief defines the scope, a project plan would define the timeline).
- Budget: Not specified.
- **Resources**: This project requires a development team proficient in Python, FastAPI, Domain-Driven Design (DDD), Clean Architecture, and containerized deployment (Docker/Kubernetes).
- **Technical Constraints**:
        - The project must use Python 3.11 or higher.
        - Poetry is the required package manager.
        - The system must be built on Clean Architecture and Domain-Driven Design (DDD) principles.
        - A PostgreSQL database with the pgvector extension (or a compatible service like Supabase) is a hard requirement for the data layer.
        - An external LLM provider (like OpenAI, Anthropic, or Ollama) and an Embedding provider are required for the RAG system to function.
        - The system must implement the full suite of documented security features (JWT, RBAC, Pydantic Validation, Rate Limiting, CORS) to be considered production-ready.

### Key Assumptions
- **User Technical Expertise**: It is assumed that the target users (AI Agent Developers) possess the technical expertise to configure, deploy, and manage a containerized application stack (Docker, Docker Compose, or Kubernetes).
- **Provider Access**: It is assumed that users will provide and manage their own database (e.g., Supabase account) and LLM/Embedding API keys (e.g., OpenAI API key).
- **Market Need**: The project assumes that developers prefer a comprehensive, standalone "knowledge engine" service over a simpler library, valuing the pre-built, production-grade infrastructure (security, performance, scalability).
- **Architectural Value**: It is assumed that the upfront complexity of Clean Architecture and DDD is a worthwhile trade-off for the long-term benefits of maintainability, testability, and extensibility.
- **Performance**: It is assumed that the defined performance stack (FastAPI, Redis caching, pgvector, batch processing) will be sufficient to meet the target performance and latency benchmarks (e.g., 250ms p95 for search).

## Risks & Open Questions

### Key Risks
- **Risk 1**: Architectural Complexity: The use of Domain-Driven Design (DDD) and Clean Architecture is a significant asset but also a risk. It requires a high level of team discipline and expertise to maintain, potentially slowing down onboarding for new developers unfamiliar with these patterns.
- **Risk 2**: Security Implementation Gap: The project specifies a comprehensive, production-grade security model (JWT, RBAC, Rate Limiting). A key risk is a gap between the architectural design and the implementation, where any missed security check could expose the entire engine to vulnerabilities.
- **Risk 3**: RAG Performance at Scale: The RAG system (chunking, hybrid search) is central to the product's value. While the architecture (Async, Redis, pgvector) is designed for performance, this remains a risk area that will require continuous benchmarking and optimization as document-load and query-volume scale.
- **Risk 4**: Deployment Complexity for Users: The reliance on a full containerized stack (Docker, Kubernetes) is robust but may present a high barrier to entry for individual developers or small teams who are not proficient in DevOps, potentially hindering adoption.

### Open Questions
- What is the detailed strategy for implementing Multi-tenant Support (v2.1)? How will data be isolated (e.g., schema per tenant, shared schema with RLS)?
- How will Event Sourcing & CQRS (v2.2) be introduced into the existing DDD architecture? Will this be a full rewrite of the persistence layer or applied only to new components?
- What are the actual performance benchmarks? The current documentation notes "dummy values," so the real-world performance under load is still an open question.
- What is the strategy for managing and migrating database schemas (via Alembic) in a zero-downtime production environment, especially with long-running agent tasks?

### Areas Needing Further Research
- **Advanced RAG Strategies (v2.2)**: The roadmap explicitly calls this out. Research is needed into more advanced retrieval, re-ranking, and synthesis techniques to stay ahead of basic RAG implementations.
- **Multi-modal RAG (v3.0)**: A significant research effort is required to determine the best-practice architecture for ingesting, chunking, embedding, and querying against image and audio data.
- **Microservices Decomposition (v3.0)**: The migration path from the v2.0 monolith to a full microservices architecture needs to be researched and defined. This includes identifying service boundaries, managing inter-service communication (via a service mesh), and handling distributed transactions.

## Appendices

### A. Research Summary 
No formal market research, competitive analysis, or user interview documents were provided for this brief. However, the project's "Acknowledgments" section and technical differentiation imply a competitive analysis against frameworks like LangChain, and the "Architecture" section indicates a deep analysis of software design principles (DDD, Clean Architecture, SOLID).

### B. Stakeholder Input 
No specific stakeholder feedback was included in the provided project documentation.

### C. References 
- **Website**: https://contextiva.dev
- **Documentation**: https://docs.contextiva.dev
- **Blog**: https://blog.contextiva.dev
- **GitHub Issues**: https://github.com/yourusername/contextiva/issues
- **GitHub Discussions**: https://github.com/yourusername/contextiva/discussions
- **Key Technology Acknowledgments**:
        - FastAPI
        - Pydantic
        - Supabase
        - LangChain (for concepts)
        - OpenAI