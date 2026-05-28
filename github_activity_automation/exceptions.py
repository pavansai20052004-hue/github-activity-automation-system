class AutomationError(Exception):
    """Base class for recoverable automation errors."""


class ConfigError(AutomationError):
    """Raised when the config file is missing or invalid."""


class MissingCredentialError(AutomationError):
    """Raised when a required environment variable is missing."""


class GitHubAPIError(AutomationError):
    """Raised for GitHub REST API failures."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RepositorySelectionError(AutomationError):
    """Raised when no repository can be selected."""


class LockError(AutomationError):
    """Raised when another automation run already owns the runtime lock."""
