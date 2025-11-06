# Security

## Input Validation
- **Validation Library**: Pydantic (from Tech Stack).
- **Validation Location**: All input validation MUST occur at the API Layer (src/api/v1/schemas/). The Application and Domain layers can trust that data has been validated.
- **Required Rules**:
        - All external inputs (request bodies, query parameters) MUST be validated by a Pydantic schema (NFR3).
        - Use strict types where possible (e.g., UUID, EmailStr).
        - Whitelist approach is preferred; do not accept arbitrary JSON blobs.

## Authentication & Authorization
- **Auth Method**: JWT Bearer Tokens, as required by NFR2.
- **Session Management**: The system is stateless. The JWT token MUST be validated on every request.
- **Required Patterns**:
        - All API endpoints (except GET /api/v1/health and POST /api/v1/auth/token) MUST be protected by the FastAPI dependency (get_current_user) defined in Story 1.4.
        - The system MUST implement Role-Based Access Control (RBAC) (NFR2). A stub for this will be created in Story 1.4, and it must be fully implemented to control access (e.g., only a project owner can delete a project).

## Secrets Management
- **Development**: All secrets (DB passwords, LLM API keys) MUST be loaded from environment variables (.env file) via the settings.py module.
- **Production**: Secrets will be injected into the container as environment variables via the deployment platform (e.g., Docker Compose, Kubernetes Secrets).
- **Code Requirements**:
        - NEVER hardcode secrets (API keys, passwords, tokens) in any Python file.
        - NEVER print() or log() a secret or a full environment object.
        - Access secrets ONLY via the settings.py configuration object. 

## API Security
- **Rate Limiting**: A rate limiter (e.g., slowapi) MUST be implemented and configured on all sensitive endpoints, especially /rag/query and /auth/token, to prevent abuse (NFR3).
- **CORS Policy**: A strict CORS policy MUST be configured in the FastAPI app to only allow requests from known, trusted origins. For development, a permissive policy is acceptable, but it must be locked down for production (NFR3).
- **Security Headers**: (e.g., X-Content-Type-Options, Strict-Transport-Security) will be added via middleware.
- **HTTPS Enforcement**: The production deployment (Kubernetes Ingress) MUST enforce HTTPS.

## Data Protection
- **Encryption at Rest**: Handled by the cloud database provider (e.g., Supabase, AWS RDS).
- **Encryption in Transit**: Enforced by HTTPS on the API.
- **PII Handling**: The Project, Document, and Task models do not inherently store PII, but the KnowledgeItem chunks might. The system assumes that any PII is the responsibility of the user who ingests the document.
- **Logging Restrictions**: No secrets, PII, or auth tokens are to be logged.

## Dependency Security
- **Scanning Tool**: Bandit (as defined in the Test Strategy) MUST be run as part of the CI pipeline to scan for common vulnerabilities.
- **Update Policy**: Dependencies will be reviewed and updated regularly.
- **Approval Process**: All new third-party libraries MUST be approved before being added to pyproject.toml.

## Security Testing
- **SAST Tool**: Bandit (Static Analysis).
- **DAST Tool**: (Deferred to post-MVP).
- **Penetration Testing**: (Deferred to post-MVP).

</div>