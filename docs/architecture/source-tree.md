# Source Tree

```Plaintext
contextiva/
├── pyproject.toml
├── README.md
├── docker-compose.yml
├── .env.example
├── migration/
│   └── [SQL migration files]
├── src/
│   ├── __init__.py
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── settings.py
│   │   │   ├── database.py
│   │   │   └── logging.py
│   │   ├── domain/
│   │   │   ├── __init__.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── project.py
│   │   │   │   ├── document.py
│   │   │   │   ├── task.py
│   │   │   │   ├── knowledge.py
│   │   │   │   └── base.py
│   │   │   ├── value_objects/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── identifiers.py
│   │   │   │   └── metadata.py
│   │   │   └── events/
│   │   │       ├── __init__.py
│   │   │       └── domain_events.py
│   │   ├── infrastructure/
│   │   │   ├── __init__.py
│   │   │   ├── database/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── supabase_client.py
│   │   │   │   ├── repositories/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── base.py
│   │   │   │   │   ├── project_repository.py
│   │   │   │   │   ├── document_repository.py
│   │   │   │   │   ├── task_repository.py
│   │   │   │   │   └── knowledge_repository.py
│   │   │   │   └── unit_of_work.py
│   │   │   ├── external/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── llm/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── provider_factory.py
│   │   │   │   │   ├── providers/
│   │   │   │   │   │   ├── __init__.py
│   │   │   │   │   │   ├── base.py
│   │   │   │   │   │   ├── openai_provider.py
│   │   │   │   │   │   ├── anthropic_provider.py
│   │   │   │   │   │   └── ollama_provider.py
│   │   │   │   │   └── embeddings/
│   │   │   │   │       ├── __init__.py
│   │   │   │   │       ├── embedding_service.py
│   │   │   │   │       └── contextual_embedding.py
│   │   │   │   └── crawler/
│   │   │   │       ├── __init__.py
│   │   │   │       └── crawler_client.py
│   │   │   └── cache/
│   │   │       ├── __init__.py
│   │   │       └── redis_cache.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── errors.py
│   │       ├── validators.py
│   │       └── helpers.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── dependencies.py
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── logging_middleware.py
│   │   │   ├── error_handler.py
│   │   │   └── auth_middleware.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── projects.py
│   │   │   │   ├── documents.py
│   │   │   │   ├── tasks.py
│   │   │   │   ├── knowledge.py
│   │   │   │   ├── rag.py
│   │   │   │   └── health.py
│   │   │   └── schemas/
│   │   │       ├── __init__.py
│   │   │       ├── requests.py
│   │   │       ├── responses.py
│   │   │       └── common.py
│   │   └── lifespan.py
│   ├── application/
│   │   ├── __init__.py
│   │   ├── use_cases/
│   │   │   ├── __init__.py
│   │   │   ├── projects/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── create_project.py
│   │   │   │   ├── get_project.py
│   │   │   │   ├── update_project.py
│   │   │   │   └── delete_project.py
│   │   │   ├── documents/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── create_document.py
│   │   │   │   ├── update_document.py
│   │   │   │   └── version_document.py
│   │   │   ├── tasks/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── create_task.py
│   │   │   │   ├── update_task_status.py
│   │   │   │   └── assign_task.py
│   │   │   └── knowledge/
│   │   │       ├── __init__.py
│   │   │       ├── ingest_document.py
│   │   │       ├── search_knowledge.py
│   │   │       └── extract_code.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── project_service.py
│   │   │   ├── document_service.py
│   │   │   ├── task_service.py
│   │   │   ├── knowledge_service.py
│   │   │   └── rag_service.py
│   │   └── dto/
│   │       ├── __init__.py
│   │       └── [Data Transfer Objects]
│   ├── mcp/
│   │   ├── __init__.py
│   │   ├── server.py
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── projects.py
│   │   │   ├── documents.py
│   │   │   ├── tasks.py
│   │   │   └── rag.py
│   │   └── context.py
│   └── agents/
│       ├── __init__.py
│       ├── server.py
│       ├── base_agent.py
│       ├── document_agent.py
│       └── rag_agent.py
└── tests/
    ├── __init__.py
    ├── unit/
    ├── integration/
    └── e2e/
```
