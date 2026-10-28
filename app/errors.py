"""Shared error types.

Every expected failure is raised as one of these classes. The app turns them
into a JSON response like {"detail": "..."} with the right HTTP status code.
This keeps the routes short: they raise an error instead of building responses
by hand in many places.
"""


class AppError(Exception):
    """An expected error that is safe to show to the user."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class DocumentValidationError(AppError):
    """A problem with an uploaded file: wrong type, too big, empty, or unreadable."""


class LLMError(AppError):
    """A problem talking to the AI service: timeout, rate limit, or a bad reply."""


class LLMConfigurationError(AppError):
    """The AI service was requested but is not set up (for example, no API key)."""
