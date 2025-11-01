# Contextiva Knowledge Engine - Modern Architecture

## Overview

This is a complete build of the Contextiva project following modern software engineering principles, design patterns, and clean architecture.

## Architecture Principles

### 1. **Domain-Driven Design (DDD)**
- **Domain Layer**: Core business logic and entities
- **Application Layer**: Use cases and orchestration
- **Infrastructure Layer**: External dependencies
- **API Layer**: HTTP interfaces

### 2. **SOLID Principles**
- Single Responsibility: Each class has one reason to change
- Open/Closed: Open for extension, closed for modification
- Liskov Substitution: Subtypes are substitutable
- Interface Segregation: Small, focused interfaces
- Dependency Inversion: Depend on abstractions

### 3. **Design Patterns Used**

#### Structural Patterns
- **Repository Pattern**: Data access abstraction
- **Factory Pattern**: Object creation (LLM providers)
- **Dependency Injection**: Loose coupling via FastAPI

#### Behavioral Patterns
- **Command Pattern**: Use cases as commands
- **Strategy Pattern**: Pluggable search strategies
- **Observer Pattern**: Domain events

#### Creational Patterns
- **Singleton**: Settings configuration
- **Builder**: Complex object construction

## Layer Architecture

```
┌─────────────────────────────────────────────┐
│           API Layer (FastAPI)               │
│  - REST endpoints                           │
│  - Request/Response DTOs                    │
│  - Dependency injection                     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│         Application Layer                   │
│  - Use Cases (business operations)          │
│  - Application Services                     │
│  - DTOs and Mappers                         │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│           Domain Layer                      │
│  - Entities & Aggregates                    │
│  - Value Objects                            │
│  - Domain Events                            │
│  - Business Rules                           │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│       Infrastructure Layer                  │
│  - Repositories (Supabase)                  │
│  - External Services (LLM, Embeddings)      │
│  - Cache (Redis)                            │
│  - Message Queue                            │
└─────────────────────────────────────────────┘
```

## Key Components

### 1. Domain Models

**Base Classes:**
- `Entity`: Objects with identity
- `ValueObject`: Immutable value-based objects
- `AggregateRoot`: Consistency boundaries
- `DomainEvent`: Domain occurrences

**Aggregates:**
- `Project`: Top-level container
- `Document`: Project documentation
- `Task`: Work items
- `KnowledgeItem`: RAG content

### 2. Repositories

**Interface:**
```python
class IRepository[T]:
    async def get_by_id(id: UUID) -> T | None
    async def get_all(skip, limit) -> list[T]
    async def add(entity: T) -> T
    async def update(entity: T) -> T
    async def delete(id: UUID) -> None
    async def exists(id: UUID) -> bool
```

**Implementations:**
- `ProjectRepository`
- `DocumentRepository`
- `TaskRepository`
- `KnowledgeRepository`

### 3. Use Cases

**Pattern:**
```python
@dataclass
class UseCaseClass:
    repository: IRepository
    service: IService
    
    async def execute(command: Command) -> Result:
        # 1. Validate
        # 2. Business logic
        # 3. Persist
        # 4. Return result
```

**Examples:**
- `CreateProjectUseCase`
- `UpdateTaskStatusUseCase`
- `SearchKnowledgeUseCase`
- `IngestDocumentUseCase`

### 4. Application Services

**Responsibilities:**
- Orchestrate multiple use cases
- Handle cross-aggregate operations
- Coordinate infrastructure services

**Services:**
- `ProjectService`: Project operations
- `RAGService`: Search and retrieval
- `DocumentService`: Document management
- `TaskService`: Task workflow

### 5. Infrastructure Services

**LLM Providers:**
```python
class ILLMProvider:
    async def complete(prompt) -> str
    async def stream(prompt) -> AsyncIterator
    async def embed(text) -> list[float]
```

**Implementations:**
- `OpenAIProvider`
- `AnthropicProvider`
- `OllamaProvider`
- `OpenRouterProvider`

## API Design

### REST Principles
- Resource-based URLs
- HTTP verbs (GET, POST, PUT, DELETE)
- Status codes (200, 201, 400, 404, 500)
- JSON responses

### Endpoints Structure

```
/api/v1/projects
  GET    /           - List projects
  POST   /           - Create project
  GET    /{id}       - Get project
  PUT    /{id}       - Update project
  DELETE /{id}       - Delete project
  POST   /{id}/archive - Archive project

/api/v1/documents
  GET    /           - List documents
  POST   /           - Create document
  GET    /{id}       - Get document
  PUT    /{id}       - Update document
  DELETE /{id}       - Delete document

/api/v1/tasks
  GET    /           - List tasks
  POST   /           - Create task
  GET    /{id}       - Get task
  PUT    /{id}       - Update task
  DELETE /{id}       - Delete task

/api/v1/rag
  POST   /query     - Semantic search
  POST   /ingest    - Ingest documents
  GET    /sources   - List sources

/api/v1/knowledge
  GET    /items     - List knowledge items
  POST   /crawl     - Crawl URL
  POST   /upload    - Upload document
```

## Configuration Management

### Settings Hierarchy
1. Default values in code
2. `.env` file
3. Environment variables
4. Database settings (runtime)

### Configuration Structure
```python
Settings
├── DatabaseSettings
├── LLMSettings
├── EmbeddingSettings
├── RAGSettings
├── CacheSettings
├── ObservabilitySettings
└── APISettings
```

## Error Handling

### Exception Hierarchy
```
Exception
└── DomainException
    ├── ValidationError
    ├── BusinessRuleViolation
    └── NotFoundError
└── ApplicationError
└── InfrastructureError
```

### Error Response Format
```json
{
  "success": false,
  "error": "Description",
  "code": "ERROR_CODE",
  "details": {...}
}
```

## Testing Strategy

### Layers
1. **Unit Tests**: Domain logic
2. **Integration Tests**: Repository layer
3. **E2E Tests**: API endpoints

### Test Structure
```
tests/
├── unit/
│   ├── domain/
│   ├── use_cases/
│   └── services/
├── integration/
│   ├── repositories/
│   └── external/
└── e2e/
    └── api/
```

## Deployment

### Docker Compose Services
```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
  
  mcp:
    build: ./mcp
    ports:
      - "8051:8051"
  
  agents:
    build: ./agents
    ports:
      - "8052:8052"
  
  postgres:
    image: supabase/postgres
  
  redis:
    image: redis:alpine
```

## Performance Considerations

### Optimization Strategies
1. **Connection Pooling**: Database connections
2. **Caching**: Redis for frequent queries
3. **Pagination**: Limit result sets
4. **Async Operations**: Non-blocking I/O
5. **Batch Processing**: Bulk operations

### Monitoring
- Request/response times
- Database query performance
- LLM API latency
- Error rates
- Resource usage

## Security

### Measures
1. **Authentication**: JWT tokens
2. **Authorization**: Role-based access
3. **Input Validation**: Pydantic models
4. **SQL Injection**: Parameterized queries
5. **Rate Limiting**: API throttling
6. **CORS**: Controlled origins

## Migration Path

### From Old to New
1. **Phase 1**: Deploy new infrastructure
2. **Phase 2**: Migrate database schema
3. **Phase 3**: Deploy API service
4. **Phase 4**: Update clients
5. **Phase 5**: Decommission old services

### Data Migration
```sql
-- Run migration scripts
-- Update schema
-- Transform data
-- Validate integrity
```

## Development Workflow

### Git Workflow
```
main (production)
  ↑
develop (staging)
  ↑
feature/* (development)
```

### CI/CD Pipeline
1. Lint & Format (Ruff, Black)
2. Type Check (MyPy)
3. Unit Tests
4. Integration Tests
5. Build Docker Images
6. Deploy to Staging
7. E2E Tests
8. Deploy to Production

## Future Enhancements

### Roadmap
1. **Event Sourcing**: Complete audit trail
2. **CQRS**: Separate read/write models
3. **Microservices**: Service decomposition
4. **GraphQL**: Alternative API
5. **Real-time**: WebSocket support
6. **Multi-tenancy**: Organization support

## Documentation

### Standards
- **Code**: Docstrings (Google style)
- **API**: OpenAPI/Swagger
- **Architecture**: ADRs (Architecture Decision Records)
- **User**: End-user documentation

## Conclusion

This architecture provides:
- ✅ Separation of concerns
- ✅ Testability
- ✅ Maintainability
- ✅ Scalability
- ✅ Extensibility

It follows industry best practices and is production-ready.