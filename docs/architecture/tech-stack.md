# Tech Stack

## Cloud Infrastructure
- **Provider**: Supabase (or any cloud provider's PostgreSQL service, e.g., AWS RDS, Azure, GCP)
- **Key Services**: PostgreSQL (with pgvector extension), Redis (e.g., ElastiCache, Memorystore, or container)
- **Deployment Regions**: User-defined (e.g., us-east-1)

## Technology Stack Table

| Category       | Technology       | Version | Purpose                     | Rationale                                                                 |
|----------------|------------------|----------|------------------------------|---------------------------------------------------------------------------|
| Language       | Python           | 3.11+    | Primary development language | Modern, async-capable, and has a rich ML/AI ecosystem. [cite: 758]        |
| Framework      | FastAPI          | 0.109+   | Backend framework            | High-performance, async, built-in data validation. [cite: 760]            |
| Runtime        | Uvicorn          | ~        | ASGI server                  | Runs the FastAPI application. [cite: 759]                                 |
| Package Mgr    | Poetry           | ~        | Dependency management        | Manages packages and virtual environments.                                |
| Database       | PostgreSQL       | 15+      | Primary data store           | Robust, reliable SQL database.                                            |
| Vector Ext.    | pgvector         | ~        | Vector storage/search        | Integrates vector search directly into PostgreSQL.                        |
| Cache          | Redis            | 7.x      | Caching layer                | Fast in-memory store for repeated queries.                                |
| Migrations     | Alembic          | ~        | Database migrations          | Manages database schema changes.                                          |
| LLM Interface  | Factory          | n/a      | Pluggable LLM provider       | PRD requirement (NFR8) for extensibility.                                 |
| LLM Provider   | OpenAI           | ~        | LLM service                  | (e.g., gpt-4o-mini)                                                      |
| LLM Provider   | Anthropic        | ~        | LLM service                  | (e.g., claude-3-haiku)                                                   |
| LLM Provider   | Ollama           | ~        | Local LLM service            | Supports local/offline models.                                            |
| LLM Provider   | OpenRouter       | ~        | LLM aggregation service      | Access to 100+ models.                                                    |
| Embeddings     | OpenAI           | ~        | Embedding service            | (e.g., text-embedding-3-small)                                            |
| Auth           | JWT / Passlib    | ~        | Authentication / Hashing     | Secure token-based auth and password hashing.                             |
| Validation     | Pydantic         | v2       | Data validation              | Enforces API schemas and settings.                                        |
| Testing        | Pytest           | ~        | Testing framework            | Standard for Python testing.                                              |
| Linting        | Ruff             | ~        | Linter                       | Fast, all-in-one linter.                                                  |
| Formatting     | Black            | ~        | Code formatter               | Enforces consistent code style.                                           |
| Type Check     | MyPy             | ~        | Static type checker          | Enforces type safety.                                                     |
