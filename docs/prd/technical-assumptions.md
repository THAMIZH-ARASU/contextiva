# Technical Assumptions
These technical decisions are derived from the Project Brief and serve as hard constraints for the architecture.

## Repository Structure: Monorepo
- A monorepo structure will be used.
- **Rationale**: This approach is ideal for a Clean Architecture, allowing for clear separation of concerns (e.g., src/api, src/application, src/domain, src/infrastructure) and easier management of shared code, such as domain models and DTOs, within a single repository.

## Service Architecture: Monolith (Clean Architecture)
- The service will be built as a single deployable unit (a monolith) following Clean Architecture and Domain-Driven Design (DDD) principles.
- **Rationale**: This provides a robust, maintainable, and testable codebase. While the "Roadmap" (v3.0) envisions a microservices architecture, the v2.0 MVP is a monolith, which is simpler to build and deploy initially.

## Testing Requirements: Full Testing Pyramid
- The project will require a comprehensive testing strategy:
- **Unit Tests (pytest)**: For domain logic and use cases.
- **Integration Tests (pytest)**: For the infrastructure layer (e.g., repository pattern against a test database).
- **E2E Tests (pytest)**: For the API endpoints.
- **Rationale**: The goal of a "production-ready" engine (NFR1) necessitates a high degree of reliability, which can only be achieved with a full testing pyramid.

## Additional Technical Assumptions and Requests
- **Language/Framework**: Python 3.11+ and FastAPI are mandatory.
- **Database**: PostgreSQL with pgvector extension (or Supabase) is mandatory.
- **Cache**: Redis is a required component for performance.
- **Security**: The full security stack (JWT, RBAC, Pydantic Validation, Rate Limiting, CORS) is a non-negotiable requirement.
- **API**: The system must expose both a REST API and an MCP Server.
