# Requirements

## Functional
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
