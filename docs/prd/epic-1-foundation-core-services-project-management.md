# Epic 1: Foundation & Core Services (Project Management)
**Epic Goal**: Establish the full production-ready application foundation—including the Clean Architecture, database (pgvector), deployment (Docker), security (JWT/RBAC stubs), and logging—while delivering the core, secured Project Management API endpoints. This epic delivers the complete, testable "scaffolding" and the first piece of core domain value.

## Story 1.1: Project Foundation & Scaffolding
As a AI Agent Developer, I want a new project repository initialized with the complete Clean Architecture directory structure and core dependencies, so that I can immediately start development following DDD principles.

### Acceptance Criteria:
- A pyproject.toml file is created, managed by poetry, with Python 3.11+ specified.
- Core dependencies are added: fastapi, pydantic, uvicorn, asyncpg (for Supabase/PostgreSQL), redis, python-jose[cryptography] (for JWT), and passlib[bcrypt] (for auth).
- The complete Clean Architecture directory structure is scaffolded (e.g., `src/api`, `src/application`, `src/domain`, `src/infrastructure`, `src/shared`).
- Basic alembic migration setup is created in a migration/ folder.
- Base configuration files are created: README.md, .env.example, .gitignore, and a docker-compose.yml (defining api, postgres, and redis services).
- `src/api/main.py` is created with a basic FastAPI app instance and a `/api/docs` (Swagger) endpoint.
- A health check endpoint (GET `/api/v1/health`) is implemented and returns a 200 OK status.

## Story 1.2: Database & Observability Integration
As a AI Agent Developer, I want the FastAPI application to be fully connected to the PostgreSQL/pgvector database and a structured logging system, so that the application is ready for persistence and observability.

### Acceptance Criteria:
- A `src/shared/config/settings.py` module is created to load all database and logging settings from environment variables.
- A database connection module (e.g., `src/shared/infrastructure/database/connection.py`) is created and manages the connection pool.
- An Alembic migration is created and run to enable the pgvector extension in the database.
- A structured logging module (`src/shared/config/logging.py`) is created and integrated into the FastAPI app to output JSON-formatted logs (NFR9).
- A middleware is added to log all incoming API requests with a unique request ID (NFR9).
The health check endpoint (GET `/api/v1/health`) is updated to successfully verify database connectivity.

## Story 1.3: Core Domain Model (Project) & Repository
As a AI Agent Developer, I want the Project domain model, repository interface, and concrete implementation defined, so that I can build business logic independent of the database.

### Acceptance Criteria:
- The Project entity is defined in `src/domain/models/project.py` with core attributes (id, name, description, status, tags) and business rules (NFR1).
- The IProjectRepository abstract base class (interface) is defined in `src/domain/models/project.py`.
- The concrete ProjectRepository implementation is created in `src/infrastructure/database/repositories/project_repository.py`, implementing the interface.
- Unit tests for the Project domain model's business logic (if any) are created.
- Integration tests for the ProjectRepository are created, verifying all CRUD operations against a test database.

## Story 1.4: Security & Auth Foundation
As a AI Agent Developer, I want a basic JWT token creation and validation system in place, so that I can secure all future API endpoints.

### Acceptance Criteria:
- A security utility module is created to handle JWT token creation (e.g., `create_access_token`) and decoding/validation (NFR2).
- A basic User domain model (with hashed_password) and UserRepository are created (following the pattern from 1.3).
- A simple POST `/api/v1/auth/token` endpoint is created that accepts a username/password (for testing) and returns a valid JWT.
- A FastAPI dependency (get_current_user) is created to protect endpoints, which validates the JWT and returns the user model.
- Stub files/classes for Role-Based Access Control (RBAC) are created (e.g., in `src/api/dependencies.py`), but the complex logic is deferred (NFR2).

## Story 1.5: Project Management API (CRUD)
As a AI Agent Developer, I want to perform full CRUD operations on Projects via the secured REST API, so that I can manage my agent's knowledge projects.

### Acceptance Criteria:
- All Project API endpoints (except OPTIONS) are protected by the JWT authentication dependency from Story 1.4 (AC 1.4).
- POST `/api/v1/projects`: Creates a new project, validates input using a Pydantic schema, and returns the created project.
- GET `/api/v1/projects`: Lists all projects for the authenticated user, supporting pagination.
- GET `/api/v1/projects/{id}`: Retrieves a single project by its ID, ensuring the user has access.
- PUT `/api/v1/projects/{id}`: Updates an existing project, validating input and access.
- DELETE `/api/v1/projects/{id}`: Deletes an existing project, ensuring the user has access.
- E2E tests are created for all 5 endpoints, verifying functionality, authentication, authorization (basic access), and Pydantic validation error handling.
