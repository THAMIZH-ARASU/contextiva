class ProjectNotFoundError(Exception):
    """Raised when a Project cannot be found by the provided identifier."""


class UserNotFoundError(Exception):
    """Raised when a User cannot be found by the provided identifier."""


class InvalidCredentialsError(Exception):
    """Raised when authentication credentials are invalid."""


class ValidationError(Exception):
    """Raised for domain validation errors when mapping from external inputs."""


class DocumentNotFoundError(Exception):
    """Raised when a Document cannot be found by the provided identifier."""


class InvalidDocumentVersionError(Exception):
    """Raised when a document version format is invalid."""


class DuplicateDocumentError(Exception):
    """Raised when attempting to create a duplicate document content_hash."""


class TaskNotFoundError(Exception):
    """Raised when a Task cannot be found by the provided identifier."""


class CircularDependencyError(Exception):
    """Raised when a task has a circular dependency (depends on itself)."""


class KnowledgeItemNotFoundError(Exception):
    """Raised when a KnowledgeItem cannot be found by the provided identifier."""


# LLM Provider Exceptions


class LLMProviderError(Exception):
    """Base exception for all LLM provider errors."""


class LLMAuthenticationError(LLMProviderError):
    """Raised when LLM provider authentication fails (401, 403 errors)."""


class LLMRateLimitError(LLMProviderError):
    """Raised when LLM provider rate limit is exceeded (429 errors)."""


class LLMConnectionError(LLMProviderError):
    """Raised when network connection to LLM provider fails."""


class UnsupportedProviderError(LLMProviderError):
    """Raised when an unsupported or unknown provider name is requested."""


class TextExtractionError(Exception):
    """Raised when text extraction from a file fails."""


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""


class DatabaseError(Exception):
    """Raised when database operations fail."""


class CrawlError(Exception):
    """Raised when web crawling operations fail."""
