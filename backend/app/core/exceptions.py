class AppError(Exception):
    """Base application error with a user-safe message."""


class AIProviderError(AppError):
    pass


class RepositoryError(AppError):
    pass


class IndexingError(AppError):
    pass


class TestExecutionError(AppError):
    pass
