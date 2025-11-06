# Core Workflows

## Workflow 1: Knowledge Ingestion (File Upload)
This diagram illustrates the asynchronous process for ingesting a new document, as defined in PRD Story 2.5. The API returns an immediate acknowledgment while processing, chunking, and embedding happen in the background.

```mermaid
sequenceDiagram
    actor Client as Developer
    participant API as API Layer (FastAPI)
    participant App as Application Layer (IngestUseCase)
    participant Infra_Doc as Doc Repository (Infra)
    participant Infra_LLM as LLM Factory (Infra)
    participant Infra_KB as KB Repository (Infra)

    Client->>+API: POST /api/v1/knowledge/upload (file.pdf)
    API->>+App: execute_ingest(file, project_id)
    
    opt Immediate API Response
        App->>API: return {"status": "processing"}
        API-->>-Client: 202 Accepted
    end

    par Background Processing 
        App->>+Infra_Doc: create_document(name, type, project_id)
        Infra_Doc-->>-App: Document(id="doc_123")

        App->>App: extract_text(file.pdf)
        App->>App: chunk_text(text)
        App->>+Infra_LLM: embed_text_chunks(chunks)
        Infra_LLM-->>-App: [vector1, vector2, ...]

        loop For Each Chunk
            App->>+Infra_KB: save_knowledge_item(doc_id, chunk, vector)
            Infra_KB-->>-App: KnowledgeItem(id="k_456")
        end

        App->>+Infra_Doc: update_document_status(id="doc_123", status="completed")
        Infra_Doc-->>-App: ok
    end
```

## Workflow 2: Knowledge Retrieval (Agentic RAG Query)
This diagram illustrates the full end-to-end "Agentic RAG" query, as defined in PRD Story 3.3. It includes retrieval, re-ranking, and final synthesis, as well as a basic error path.

```mermaid
sequenceDiagram
    actor Client as AI Agent
    participant API as API Layer (FastAPI)
    participant App as Application Layer (RAGUseCase)
    participant Infra_KB as KB Repository (Infra)
    participant Infra_LLM as LLM Factory (Infra)
    participant External_LLM as LLM Provider (e.g., OpenAI)

    Client->>+API: POST /api/v1/rag/query (query="...", use_agentic_rag=true)
    API->>+App: execute_query(query, project_id, flags)

    App->>+Infra_LLM: embed_text(query)
    Infra_LLM->>+External_LLM: POST /v1/embeddings
    External_LLM-->>-Infra_LLM: query_vector
    Infra_LLM-->>-App: query_vector

    App->>+Infra_KB: hybrid_search(query_vector, "query text")
    Infra_KB-->>-App: [chunk1, chunk2, chunk3]

    App->>+Infra_LLM: rerank_chunks(query, chunks)
    Infra_LLM->>+External_LLM: POST /v1/chat/completions (re-rank prompt)
    External_LLM-->>-Infra_LLM: [chunk2, chunk1, chunk3]
    Infra_LLM-->>-App: reordered_chunks

    App->>+Infra_LLM: synthesize_answer(query, reordered_chunks)
    Infra_LLM->>+External_LLM: POST /v1/chat/completions (synthesis prompt)
    External_LLM-->>-Infra_LLM: "This is the synthesized answer."
    Infra_LLM-->>-App: "This is the synthesized answer."

    App-->>-API: RAGResult(answer="...", chunks=[...])
    API-->>-Client: 200 OK (RAGResult)

    alt Query Fails (e.g., DB Error)
        App->>+Infra_KB: hybrid_search(...)
        Infra_KB-->>-App: DatabaseConnectionError
        App-->>API: Error(code="DB_ERROR", ...)
        API-->>Client: 500 Internal Server Error
    end
```
