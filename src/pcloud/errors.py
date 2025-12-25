# Exceptions
class AuthenticationError(Exception):
    """Authentication failed"""


class OnlyPcloudError(NotImplementedError):
    """Feature restricted to pCloud"""


class NoSessionError(Exception):
    """Raised when the session is not connected."""
    def __init__(self, message="Not connected to PCloud API, call connect() first."):
        super().__init__(message)


class NoTokenError(Exception):
    """Raised when the token is missing."""
    def __init__(self, message="PCloud token is missing."):
        super().__init__(message)