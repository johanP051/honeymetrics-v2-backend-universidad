"""Domain-level failures shared by services and translated at the API boundary."""


class DomainError(Exception):
    """Base class for expected business and authentication failures."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class AuthenticationError(DomainError):
    """Credentials or a one-time authentication proof were rejected."""


class ValidationError(DomainError, ValueError):
    """A business rule or submitted value was rejected (HTTP 400 contract)."""


class InvalidInputError(DomainError):
    """A domain input is invalid (HTTP 422 contract)."""


class ResourceNotFoundError(DomainError):
    """A requested domain resource does not exist."""
