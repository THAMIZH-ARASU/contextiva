# Test Strategy and Standards

## Testing Philosophy
- **Approach**: The project will follow a Test-Driven Development (TDD) approach for the domain and application layers. For the api and infrastructure layers, a Test-After approach will be used. This aligns with the "Full Testing Pyramid"  requirement from the PRD.
- **Coverage Goals**:
        - `domain` Layer: 95%+
        - `application` Layer: 90%+
        - `infrastructure` Layer: 80%+
        - Overall Project: 85%+
- **Test Pyramid**: The strategy emphasizes a large base of fast unit tests, a significant layer of integration tests, and a small, focused set of E2E tests.

## Test Types and Organization

## Unit Tests
- **Framework**: Pytest (from Tech Stack).
- **File Convention**: test_*.py (e.g., tests/unit/domain/models/test_project.py).
- **Location**: tests/unit/ (mirroring the src/ structure).
- **Mocking Library**: pytest-mock (for unittest.mock integration).
- **Coverage Requirement**: 95% for domain, 90% for application.
- **AI Agent Requirements**:
        - Generate tests for all public methods and business logic rules.
        - Cover all edge cases and error conditions (e.g., raising custom exceptions).
        - Follow the AAA pattern (Arrange, Act, Assert).
        - Mock all external dependencies (e.g., repository interfaces, LLM provider interfaces).

## Integration Tests
- **Scope**:
        - Test infrastructure layer components (e.g., ProjectRepository) against real services.
        - Test application layer (Use Cases/Services) against the real infrastructure layer.
- **Location**: tests/integration/ (e.g., tests/integration/infrastructure/database/repositories/test_project_repository.py).
- **Test Infrastructure**:
        - **PostgreSQL/pgvector**: Use Testcontainers (or equivalent) to spin up a real PostgreSQL/pgvector database for the test session.
        - **Redis**: Use Testcontainers (or equivalent) to spin up a real Redis instance.
        - **External APIs**: Use httpx-responses or pytest-httpx for stubbing external LLM API calls.

## End-to-End (E2E) Tests
- **Framework**: Pytest with httpx as the client.
- **Scope**: Test the fully built and running FastAPI application. This involves making real HTTP requests to the API endpoints and validating the JSON responses and status codes against the OpenAPI spec.
- **Environment**: E2E tests will be run in the CI/CD pipeline against the staging environment.
- **Test Data**: Tests will be responsible for creating their own data (e.g., creating a new project via the API) and cleaning it up.

## Test Data Management
- **Strategy**: Use a combination of Pytest fixtures and the factory_boy library.
- **Fixtures**: pytest fixtures for managing dependencies (e.g., a test database session).
- **Factories**: Use factory_boy to create instances of domain models (Project, Document) for testing.
- **Cleanup**: All tests (integration and E2E) MUST run within a database transaction that is rolled back at the end of each test to ensure test isolation.

## Continuous Testing
- **CI Integration**: The GitHub Actions pipeline (.github/workflows/) MUST be configured to:
        - Run ruff (lint) and black --check (format) on all PRs.
        - Run mypy (type check) on all PRs.
        - Run all unit and integration tests on all PRs.
        - Run e2e tests after a successful deployment to staging.
- **Performance Tests**: (Deferred to post-MVP).
- **Security Tests**: Use bandit as part of the linting step in CI to perform static analysis for common security vulnerabilities.
