import logging
import requests
from flask import current_app
from app.utils.exceptions import RepositoryNotFoundError, RateLimitExceededError, UnauthorizedError

logger = logging.getLogger(__name__)

def fetch_issues(owner: str, repository: str):
    issues_url = f'https://api.github.com/repos/{owner}/{repository}/issues'

    logger.info('Fetching issues from %s', issues_url)

    github_token = current_app.config.get('GITHUB_ACCESS_TOKEN')
    if github_token:
        headers = {'Authorization': f'token {github_token}'}
    else:
        headers = {}
        logger.warning('GITHUB_ACCESS_TOKEN is not set. API rate limits may apply.')

    issues = []
    page = 1
    while True:
        params = {'state': 'all', 'per_page': 100, 'page': page}
        response = requests.get(issues_url, headers=headers, params=params, timeout=30)

        if response.status_code == 401:
            raise UnauthorizedError()

        if response.status_code in (403, 429) and response.headers.get('X-RateLimit-Remaining') == '0':
            reset_timestamp = int(response.headers.get('X-RateLimit-Reset', 0))
            raise RateLimitExceededError(reset_timestamp)

        if response.status_code == 404:
            raise RepositoryNotFoundError(owner, repository)

        if response.status_code != 200:
            response.raise_for_status()

        data = response.json()
        if not data:
            break
        issues.extend(data)
        page += 1
    return issues

def fetch_comments_for_issue(owner: str, repository: str, issue_number: str):
    comments_url = f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments'

    logger.info('Fetching issues comments from  %s', comments_url)

    github_token = current_app.config.get('GITHUB_ACCESS_TOKEN')
    if github_token:
        headers = {'Authorization': f'token {github_token}'}
    else:
        headers = {}
        logger.warning('GITHUB_ACCESS_TOKEN is not set. API rate limits may apply.')

    comments = []
    page = 1

    while True:
        params = {'per_page': 100, 'page': page}
        response = requests.get(comments_url, headers=headers, params=params, timeout=30)

        if response.status_code in (403, 429) and response.headers.get('X-RateLimit-Remaining') == '0':
            reset_timestamp = int(response.headers.get('X-RateLimit-Reset', 0))
            raise RateLimitExceededError(reset_timestamp)

        if response.status_code != 200:
            response.raise_for_status()

        data = response.json()
        if not data:
            break
        comments.extend(data)
        page += 1
    return comments
