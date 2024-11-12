import logging
import asyncio
from typing import Union, Dict, List

import httpx
from flask import current_app
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

from app.utils.exceptions import RepositoryNotFoundError, RateLimitExceededError, UnauthorizedError

logger = logging.getLogger(__name__)

async def fetch_issues(owner: str, repository: str):
    issues_url = f'https://api.github.com/repos/{owner}/{repository}/issues'

    logger.debug('Fetching issues from %s', issues_url)

    github_token = current_app.config.get('GITHUB_ACCESS_TOKEN')
    if github_token:
        headers = {'Authorization': f'token {github_token}'}
    else:
        headers = {}
        logger.warning('GITHUB_ACCESS_TOKEN is not set. API rate limits may apply.')

    issues = []
    page = 1
    async with httpx.AsyncClient() as client:
        while True:
            params = {'state': 'all', 'per_page': 100, 'page': page}
            res = await client.get(issues_url, headers=headers, params=params, timeout=30)

            if res.status_code == 401:
                raise UnauthorizedError()

            if res.status_code in (403, 429) and res.headers.get('X-RateLimit-Remaining') == '0':
                reset_timestamp = int(res.headers.get('X-RateLimit-Reset', 0))
                raise RateLimitExceededError(reset_timestamp)

            if res.status_code == 404:
                raise RepositoryNotFoundError(owner, repository)

            if res.status_code != 200:
                logger.error(
                    'Failed to fetch issues from %s. Status code: %d, Response: %s', 
                    issues_url, res.status_code, res.text
                )
                res.raise_for_status()

            data = res.json()
            if not data:
                break
            issues.extend(data)
            page += 1
    logger.debug('Successfully fetched issues from %s', issues_url)
    return issues

@retry(
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    wait=wait_exponential(multiplier=2, min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True
)
async def fetch_page_comments(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    comments_url: str,
    headers: Dict[str, str],
    params: Dict[str, Union[str, int]]
) -> List[dict]:
    async with semaphore:
        res = await client.get(comments_url, headers=headers, params=params, timeout=30)

    if res.status_code in (403, 429) and res.headers.get('X-RateLimit-Remaining') == '0':
        reset_timestamp = int(res.headers.get('X-RateLimit-Reset', 0))
        raise RateLimitExceededError(reset_timestamp)

    if res.status_code != 200:
        logger.error('Failed to fetch comments. Status code: %d, Response: %s', res.status_code, res.text)
        res.raise_for_status()

    return res.json()

async def fetch_comments_for_issue(
    semaphore: asyncio.Semaphore, owner: str, repository: str, issue_number: str
) -> List[dict]:
    comments_url = f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments'

    logger.debug('Fetching issue comments from %s', comments_url)

    github_token = current_app.config.get('GITHUB_ACCESS_TOKEN')
    if github_token:
        headers = {'Authorization': f'token {github_token}'}
    else:
        headers = {}
        logger.warning('GITHUB_ACCESS_TOKEN is not set. API rate limits may apply.')

    comments = []
    page = 1

    async with httpx.AsyncClient() as client:
        while True:
            params = {'per_page': 100, 'page': page}
            try:
                data = await fetch_page_comments(client, semaphore, comments_url, headers, params)
            except RateLimitExceededError as e:
                logger.error('Rate limit exceeded. Please try again later.')
                raise e
            except Exception as e:
                logger.error('An error occurred: %s', e)
                raise e

            if not data:
                break
            comments.extend(data)
            page += 1

    logger.debug('Successfully fetched issue comments from %s', comments_url)
    return comments
