# pylint: disable=W0621

from unittest.mock import MagicMock, AsyncMock, patch
from typing import Any

import asyncio
import pytest
import httpx
from flask import Flask

from app.services.github_client import fetch_issues, fetch_comments_for_issue
from app.utils.exceptions import (
    RepositoryNotFoundError, RateLimitExceededError, UnauthorizedError
)

@pytest.fixture
def app_context():
    app = Flask(__name__)
    app.config['GITHUB_ACCESS_TOKEN'] = 'fake_token'
    with app.app_context():
        yield

class TestFetchIssues:
    app: Flask
    app_context: Any
    def setup_method(self):
        self.app = Flask(__name__)
        self.app.config['GITHUB_ACCESS_TOKEN'] = 'test_token'
        self.app_context = self.app.app_context()
        self.app_context.push()

    def teardown_method(self):
        self.app_context.pop()

    @pytest.mark.asyncio
    @patch('app.services.github_client.httpx.AsyncClient')
    async def test_success(self, mock_async_client_class):
        mock_client = AsyncMock()
        mock_async_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            [{'id': 1, 'title': 'Issue 1'}],
            []
        ]
        mock_client.get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'
        issues = await fetch_issues(owner, repository)

        assert issues == [{'id': 1, 'title': 'Issue 1'}]
        assert mock_client.get.call_count == 2

        expected_headers = {'Authorization': 'token test_token'}
        expected_params_page1 = {'state': 'all', 'per_page': 100, 'page': 1}
        expected_params_page2 = {'state': 'all', 'per_page': 100, 'page': 2}

        mock_client.get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues',
            headers=expected_headers,
            params=expected_params_page1,
            timeout=30,
        )
        mock_client.get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues',
            headers=expected_headers,
            params=expected_params_page2,
            timeout=30,
        )

    @pytest.mark.asyncio
    @patch('app.services.github_client.httpx.AsyncClient')
    async def test_repository_not_found(self, mock_async_client_class):
        mock_client = AsyncMock()
        mock_async_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.get.return_value = mock_response

        owner = 'nonexistent_owner'
        repository = 'nonexistent_repo'

        with pytest.raises(RepositoryNotFoundError) as exc_info:
            await fetch_issues(owner, repository)

        assert str(exc_info.value) == f'Repository not found: https://github.com/{owner}/{repository}'

    @pytest.mark.asyncio
    @patch('app.services.github_client.httpx.AsyncClient')
    async def test_other_http_error(self, mock_async_client_class):
        mock_client = AsyncMock()
        mock_async_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            '500 Server Error', request=None, response=None
        )
        mock_client.get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await fetch_issues(owner, repository)

        assert '500 Server Error' in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.services.github_client.httpx.AsyncClient')
    async def test_unauthorized_error(self, mock_async_client_class):
        mock_client = AsyncMock()
        mock_async_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client.get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(UnauthorizedError):
            await fetch_issues(owner, repository)

    @pytest.mark.asyncio
    @patch('app.services.github_client.httpx.AsyncClient')
    async def test_rate_limit_exceeded(self, mock_async_client_class):
        mock_client = AsyncMock()
        mock_async_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '1234567890'}
        mock_client.get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(RateLimitExceededError) as exc_info:
            await fetch_issues(owner, repository)

        assert exc_info.value.reset_time == '2009-02-13 23:31:30'

    @pytest.mark.asyncio
    @patch('app.services.github_client.httpx.AsyncClient')
    async def test_no_github_token(self, mock_async_client_class):
        self.app.config['GITHUB_ACCESS_TOKEN'] = None

        mock_client = AsyncMock()
        mock_async_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            [{'id': 1, 'title': 'Issue 1'}],
            []
        ]
        mock_client.get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'
        issues = await fetch_issues(owner, repository)

        assert issues == [{'id': 1, 'title': 'Issue 1'}]
        assert mock_client.get.call_count == 2

        expected_headers = {}
        expected_params_page1 = {'state': 'all', 'per_page': 100, 'page': 1}
        expected_params_page2 = {'state': 'all', 'per_page': 100, 'page': 2}

        mock_client.get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues',
            headers=expected_headers,
            params=expected_params_page1,
            timeout=30,
        )
        mock_client.get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues',
            headers=expected_headers,
            params=expected_params_page2,
            timeout=30,
        )

class TestFetchCommentsForIssue:
    app: Flask
    app_context: Any
    def setup_method(self):
        self.app = Flask(__name__)
        self.app.config['GITHUB_ACCESS_TOKEN'] = 'test_token'
        self.app_context = self.app.app_context()
        self.app_context.push()

    def teardown_method(self):
        self.app_context.pop()

    @pytest.mark.asyncio
    @patch('app.services.github_client.httpx.AsyncClient')
    async def test_success(self, mock_async_client_class):
        mock_client = AsyncMock()
        mock_async_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            [{'id': 1, 'body': 'Comment 1'}, {'id': 2, 'body': 'Comment 2'}],
            []
        ]
        mock_client.get.return_value = mock_response

        semaphore = asyncio.Semaphore(5)
        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'
        comments = await fetch_comments_for_issue(semaphore, owner, repository, issue_number)

        assert comments == [{'id': 1, 'body': 'Comment 1'}, {'id': 2, 'body': 'Comment 2'}]
        assert mock_client.get.call_count == 2

        expected_headers = {'Authorization': 'token test_token'}
        expected_params_page1 = {'per_page': 100, 'page': 1}
        expected_params_page2 = {'per_page': 100, 'page': 2}

        mock_client.get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments',
            headers=expected_headers,
            params=expected_params_page1,
            timeout=30,
        )
        mock_client.get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments',
            headers=expected_headers,
            params=expected_params_page2,
            timeout=30,
        )

    @pytest.mark.asyncio
    @patch('app.services.github_client.httpx.AsyncClient')
    async def test_no_github_token(self, mock_async_client_class):
        self.app.config['GITHUB_ACCESS_TOKEN'] = None

        mock_client = AsyncMock()
        mock_async_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            [{'id': 1, 'body': 'Comment 1'}, {'id': 2, 'body': 'Comment 2'}],
            []
        ]
        mock_client.get.return_value = mock_response

        semaphore = asyncio.Semaphore(5)
        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'
        comments = await fetch_comments_for_issue(semaphore, owner, repository, issue_number)

        assert comments == [{'id': 1, 'body': 'Comment 1'}, {'id': 2, 'body': 'Comment 2'}]
        assert mock_client.get.call_count == 2

        expected_headers = {}
        expected_params_page1 = {'per_page': 100, 'page': 1}
        expected_params_page2 = {'per_page': 100, 'page': 2}

        mock_client.get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments',
            headers=expected_headers,
            params=expected_params_page1,
            timeout=30,
        )
        mock_client.get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments',
            headers=expected_headers,
            params=expected_params_page2,
            timeout=30,
        )

    @pytest.mark.asyncio
    @patch('app.services.github_client.httpx.AsyncClient')
    async def test_rate_limit_exceeded(self, mock_async_client_class):
        mock_client = AsyncMock()
        mock_async_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '1234567890'}
        mock_client.get.return_value = mock_response

        semaphore = asyncio.Semaphore(5)
        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'

        with pytest.raises(RateLimitExceededError) as exc_info:
            await fetch_comments_for_issue(semaphore, owner, repository, issue_number)

        assert exc_info.value.reset_time == '2009-02-13 23:31:30'

    @pytest.mark.asyncio
    @patch('app.services.github_client.httpx.AsyncClient')
    async def test_other_http_error(self, mock_async_client_class):
        mock_client = AsyncMock()
        mock_async_client_class.return_value.__aenter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            '500 Server Error', request=None, response=None
        )
        mock_client.get.return_value = mock_response

        semaphore = asyncio.Semaphore(5)
        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await fetch_comments_for_issue(semaphore, owner, repository, issue_number)

        assert '500 Server Error' in str(exc_info.value)

    @pytest.mark.asyncio
    @patch('app.services.github_client.fetch_page_comments')
    async def test_fetch_page_comments_rate_limit_exceeded(self, mock_fetch_page_comments):
        mock_fetch_page_comments.side_effect = RateLimitExceededError(reset_time=1234567890)

        semaphore = asyncio.Semaphore(5)
        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'

        with pytest.raises(RateLimitExceededError) as exc_info:
            await fetch_comments_for_issue(semaphore, owner, repository, issue_number)

        assert exc_info.value.reset_time == '2009-02-13 23:31:30'
        assert mock_fetch_page_comments.call_count == 1

    @pytest.mark.asyncio
    @patch('app.services.github_client.fetch_page_comments')
    async def test_fetch_page_comments_general_exception(self, mock_fetch_page_comments):
        mock_fetch_page_comments.side_effect = Exception('Unexpected Error')

        semaphore = asyncio.Semaphore(5)
        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'

        with pytest.raises(Exception) as exc_info:
            await fetch_comments_for_issue(semaphore, owner, repository, issue_number)

        assert str(exc_info.value) == 'Unexpected Error'
        assert mock_fetch_page_comments.call_count == 1

    @pytest.mark.asyncio
    @patch('app.services.github_client.fetch_page_comments')
    async def test_fetch_page_comments_empty_data(self, mock_fetch_page_comments):
        mock_fetch_page_comments.return_value = []

        semaphore = asyncio.Semaphore(5)
        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'

        comments = await fetch_comments_for_issue(semaphore, owner, repository, issue_number)

        assert comments == []
        assert mock_fetch_page_comments.call_count == 1
