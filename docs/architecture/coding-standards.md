# Coding Standards

## Core Standards
- **Languages & Runtimes**: All Python code MUST adhere to Python 3.11+ syntax.
- **Style & Linting**: All code MUST be formatted with Black and pass all Ruff linter checks before commit.
- **Test Organization**: Tests MUST be placed in the corresponding directory under `tests/` (e.g., domain logic in `tests/unit/domain/`, repository tests in `tests/integration/repositories/`).

## Naming Conventions
| Element   | Convention       | Example                |
|------------|------------------|------------------------|
| Files      | snake_case.py    | project_repository.py  |
| Classes    | PascalCase       | ProjectRepository      |
| Functions  | snake_case       | create_project         |
| Variables  | snake_case       | new_project            |
| Constants  | UPPER_SNAKE_CASE | DEFAULT_PROJECT_STATUS |

## Critical Rules
- **Rule 1**: Enforce Clean Architecture:
        - Code in the domain layer MUST NOT import from application, api, or infrastructure.
        - Code in the application layer MUST NOT import from api or infrastructure (it only imports domain interfaces).
        - Code in the api layer MUST NOT import from domain or infrastructure. It only calls the application layer.
        - Code in the infrastructure layer implements domain interfaces and depends on external libraries.
- **Rule 2**: Use the Repository Pattern:
        - All database access MUST go through a Repository interface (e.g., IProjectRepository).
        - NEVER use the SupabaseClient or asyncpg driver directly from the application or api layers.
- **Rule 3**: No Business Logic in API Layer:
        - The `api/routes/` files MUST contain zero business logic.
        - Their only job is to validate input (Pydantic), call a single Application layer use case/service, and - return the response.
- **Rule 4**: Use Custom Exceptions:
        - NEVER raise generic Exception or HTTPException from the application or domain layers.
        - ALWAYS raise specific custom exceptions (e.g., ProjectNotFoundError) defined in `shared/utils/errors.py`.
- **Rule 5**: No Hardcoded Secrets:
        - NEVER hardcode API keys, passwords, or any secrets.
        - ALWAYS load them from the `settings.py` module, which loads from environment variables.

## Language-Specific Guidelines
### Python Specifics:
- **Type Hinting**: All function definitions (including def __init__) MUST include full type hints for all arguments and return values. All code MUST pass MyPy checks.
- **Docstrings**: All public modules, classes, and functions MUST have Google-style docstrings.
- **Async**: Use async def and await for all I/O operations (database, external API calls, etc.).
