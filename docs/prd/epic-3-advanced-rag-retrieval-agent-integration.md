# Epic 3: Advanced RAG Retrieval & Agent Integration
**Epic Goal**: Expose the knowledge ingested in Epic 2 by building the complete, agent-facing query pipeline. This includes the core semantic search API, the advanced RAG features (hybrid search, re-ranking, synthesis), and the Model Context Protocol (MCP) server for native agent integration.

## Story 3.1: RAG Retrieval API (Core Query)
As a AI Agent Developer, I want a secured API endpoint to send a text query, so that I can receive the most relevant KnowledgeItems from my project.

### Acceptance Criteria:
- A new endpoint POST `/api/v1/rag/query` is created and secured using the JWT authentication dependency (from Story 1.4).
- The endpoint accepts a Pydantic schema containing at least project_id and query_text.
- The incoming query_text is converted to an embedding using the configured Embedding Provider (from Story 2.2).
- The system performs a vector similarity search (using pgvector) against KnowledgeItems that match the project_id.
- The search MUST return the top-K (e.g., K=5, configurable via `settings.py`) matching KnowledgeItem chunks.
- E2E tests are created to ingest a document (using the API from Story 2.5) and then successfully query for its content.

## Story 3.2: Advanced RAG - Hybrid Search & Re-ranking
As a AI Agent Developer, I want the RAG query endpoint to optionally support Hybrid Search and Re-ranking, so that I can improve the relevance of my search results (FR10).

### Acceptance Criteria:
- The POST `/api/v1/rag/query` endpoint is updated to accept optional boolean flags: `use_hybrid_search` and `use_re_ranking`.
- If `use_hybrid_search` is true, the system performs both vector search (from 3.1) and traditional keyword search (e.g., BM25/full-text search) and merges the results.
- If `use_re_ranking` is true, the initial set of retrieved chunks (from AC 3.1.5 or 3.2.2) is passed to an LLM provider (from Story 2.2) to re-rank them for relevance to the original query.
- Configuration in `settings.py` is added to enable/disable these features by default (e.g., RAG_USE_HYBRID_SEARCH=false, RAG_USE_RERANKING=false).
- E2E tests are updated to validate the behavior when these flags are enabled and disabled.

## Story 3.3: Advanced RAG - Agentic RAG (Synthesis)
As a AI Agent Developer, I want the RAG query endpoint to optionally return a synthesized, natural language answer, so that my agent can consume a direct response instead of just raw chunks (FR10).

### Acceptance Criteria:
- The POST `/api/v1/rag/query` endpoint is updated to accept an optional boolean flag: use_agentic_rag.
- If use_agentic_rag is true, the system takes the final (re-ranked) chunks, along with the original query, and passes them to an LLM provider (from Story 2.2) with a "summarize" or "answer based on context" prompt.
- The API response is updated to include a new optional field, synthesized_answer, containing the LLM's natural language response.
- Configuration in settings.py is added to enable/disable this feature by default (RAG_USE_AGENTIC=false).
- E2E tests are updated to validate that a synthesized answer is correctly returned when the flag is enabled.

## Story 3.4: MCP Server Integration
As a an AI Agent (programmatic client), I want to connect to a Model Context Protocol (MCP) server, so that I can natively interact with the Contextiva knowledge engine (FR12).

### Acceptance Criteria:
- An `mcp/server.py` file is created that implements the MCP specification, as defined in the project structure.
- The MCP server is configured as a new service (mcp) in the docker-compose.yml file.
- The MCP server re-uses the application services (e.g., ProjectService, RAGService) to fulfill agent requests.
- MCP tools are defined for core agent actions: create_project, ingest_document, and query_knowledge.
- The MCP server is secured using the same JWT authentication logic as the REST API.
- E2E tests are created to connect to the MCP server (e.g., via a simple client) and execute a basic query_knowledge tool call.

</div>