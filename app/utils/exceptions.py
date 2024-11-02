class MissingFieldsError(Exception):
    """Exception thrown when required fields are not filled in"""
    def __init__(self, missing_fields):
        self.missing_fields = missing_fields
        message = f"Missing fields: {', '.join(missing_fields)}"
        super().__init__(message)

class RepositoryNotFoundError(Exception):
    """Exception thrown when the specified repository cannot be found"""
    def __init__(self, owner, repo):
        message = f"Repository not found: https://github.com/{owner}/{repo}"
        super().__init__(message)
