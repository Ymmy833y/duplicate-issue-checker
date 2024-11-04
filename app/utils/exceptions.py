class MissingFieldsError(Exception):
    """Exception thrown when required fields are not filled in"""
    def __init__(self, missing_fields):
        self.missing_fields = missing_fields
        message = f"Missing fields: {', '.join(missing_fields)}"
        super().__init__(message)

class RepositoryNotFoundError(Exception):
    """Exception thrown when the specified repository cannot be found"""
    def __init__(self, owner, repo):
        message = f'Repository not found: https://github.com/{owner}/{repo}'
        super().__init__(message)

class RateLimitExceededError(Exception):
    """Exception thrown when GitHub API rate limit is exceeded"""
    def __init__(self, reset_time):
        self.reset_time = reset_time
        message = f'Rate limit exceeded. Try again after {reset_time}'
        super().__init__(message)

class UnauthorizedError(Exception):
    """Exception thrown when the GitHub API returns a 401 Unauthorized status"""
    def __init__(self, message='Unauthorized access. Please check your GITHUB_ACCESS_TOKEN'):
        super().__init__(message)
