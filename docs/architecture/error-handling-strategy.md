# Error Handling Strategy

## General Approach
- **Error Model**: We will use a custom exception-based error model. Business logic in the Application and Domain layers will raise specific custom exceptions (e.g., ProjectNotFoundError, ValidationError, BusinessRuleViolation).
- **Exception Hierarchy**: Custom exceptions will inherit from a base ContextivaException (defined in src/shared/utils/errors.py).
- **Error Propagation**: All exceptions will be caught by a centralized FastAPI middleware (src/api/middleware/error_handler.py). This middleware will be responsible for logging the full exception and returning a standardized JSON error response (e.g., {"success": false, "error": "...", "code": "..."}), mapping custom exceptions to the correct HTTP status codes (400, 404, 422, 500).

## Logging Standards
- **Library**: Standard Python logging, configured to output structured JSON logs, as required by the PRD (NFR9) and README.
- **Format**: JSON logs will include timestamp, level, message, service_name, request_id, and stack trace (for errors).
- **Levels**: Standard levels (DEBUG, INFO, WARNING, ERROR, CRITICAL) will be used.
- **Required Context**:
        - **Correlation ID**: A unique request_id (e.g., a UUID) will be generated for every incoming API request and included in all subsequent log messages for that request, enabling end-to-end request tracing (NFR9).

## Error Handling Patterns

## External API Errors
- **Retry Policy**: We will implement an exponential backoff retry policy (e.g., using the tenacity library) for transient errors when calling external LLM providers (e.g., 503, 429 Rate Limit).
- **Circuit Breaker**: (Deferred to v2.x) A circuit breaker pattern is not included in the v2.0 MVP but should be considered for future iterations to prevent cascading failures.
- **Timeout Configuration**: All external HTTP requests (to LLMs, Web Crawler) will have aggressive, non-default timeouts configured to prevent hanging requests.
- **Error Translation**: Errors from external providers will be caught and wrapped in a custom InfrastructureError exception.

## Business Logic Errors
- **Custom Exceptions**: The Domain and Application layers will raise specific exceptions (e.g., ProjectNotFoundError, DocumentVersionConflictError).
- **User-Facing Errors**: The error_handler.py middleware will map these custom exceptions to user-friendly 4xx HTTP responses. For example, ProjectNotFoundError -> 404 Not Found.
- **Error Codes**: We will implement a simple "error code" (e.g., PROJECT_NOT_FOUND) in the JSON response body to provide a stable identifier for clients.

## Data Consistency
- **Transaction Strategy**: All database operations within a single use case will be wrapped in an atomic transaction, managed by a Unit of Work (unit_of_work.py in the source tree).
- **Compensation Logic**: If any step in a use case fails (e.g., embedding fails after creating a document), the entire transaction will be rolled back, preventing orphaned data.
- **Idempotency**: (Deferred) Endpoints for creation/ingestion will be designed to be idempotent where possible (e.g., by checking content_hash before re-processing a document).
