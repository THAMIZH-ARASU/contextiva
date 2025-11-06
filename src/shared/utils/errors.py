class ProjectNotFoundError(Exception):
    """Raised when a Project cannot be found by the provided identifier."""


class ValidationError(Exception):
    """Raised for domain validation errors when mapping from external inputs."""


