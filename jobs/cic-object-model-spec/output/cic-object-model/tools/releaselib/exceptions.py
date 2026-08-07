class ReleaseError(Exception):
    """Base exception for all release-related errors."""

    def __init__(self, message, cause=None):
        super().__init__(message)
        self.cause = cause


class GitStateError(ReleaseError):
    """Exception for errors related to the Git repository's state."""

    pass


class GitServiceError(ReleaseError):
    """Exception for errors originating from the Git service wrapper."""

    pass


class VersionMismatchError(ReleaseError):
    """Exception for version string mismatches or invalid increments."""

    pass


class ConfigurationError(ReleaseError):
    """Exception for configuration-related errors (e.g., in project.yaml)."""

    pass


class VaultServiceError(ReleaseError):
    """Exception for errors originating from the Vault service."""

    pass


class ManualInterventionRequired(ReleaseError):
    """
    Custom exception to signal that the process has stopped gracefully
    and requires manual user action to continue. This is not a fatal error.
    """

    pass
