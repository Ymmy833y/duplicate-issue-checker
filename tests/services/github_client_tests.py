# pylint: disable=W0621

from unittest.mock import MagicMock, patch
from typing import Any

import pytest
import requests
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

    @patch('requests.get')
    def test_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            [{'id': 1, 'title': 'Issue 1'}],
            []
        ]
        mock_get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'
        issues = fetch_issues(owner, repository)

        assert issues == [{'id': 1, 'title': 'Issue 1'}]
        assert mock_get.call_count == 2

        expected_headers = {'Authorization': 'token test_token'}
        expected_params_page1 = {'state': 'all', 'per_page': 100, 'page': 1}
        expected_params_page2 = {'state': 'all', 'per_page': 100, 'page': 2}

        mock_get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues',
            headers=expected_headers,
            params=expected_params_page1,
            timeout=30,
        )
        mock_get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues',
            headers=expected_headers,
            params=expected_params_page2,
            timeout=30,
        )

    @patch('requests.get')
    def test_repository_not_found(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        owner = 'nonexistent_owner'
        repository = 'nonexistent_repo'

        with pytest.raises(RepositoryNotFoundError) as exc_info:
            fetch_issues(owner, repository)

        assert str(exc_info.value) == f'Repository not found: https://github.com/{owner}/{repository}'

    @patch('requests.get')
    def test_other_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError('500 Server Error')
        mock_get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(requests.HTTPError) as exc_info:
            fetch_issues(owner, repository)

        assert str(exc_info.value) == '500 Server Error'

    @patch('requests.get')
    def test_unauthorized_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(UnauthorizedError):
            fetch_issues(owner, repository)

    @patch('requests.get')
    def test_rate_limit_exceeded(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '1234567890'}
        mock_get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(RateLimitExceededError) as exc_info:
            fetch_issues(owner, repository)

        assert exc_info.value.reset_time == 1234567890

    @patch('requests.get')
    def test_no_github_token(self, mock_get):
        # Remove the token from the app config
        self.app.config['GITHUB_ACCESS_TOKEN'] = None

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            [{'id': 1, 'title': 'Issue 1'}],
            []
        ]
        mock_get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'
        issues = fetch_issues(owner, repository)

        assert issues == [{'id': 1, 'title': 'Issue 1'}]
        assert mock_get.call_count == 2

        expected_headers = {}
        expected_params_page1 = {'state': 'all', 'per_page': 100, 'page': 1}
        expected_params_page2 = {'state': 'all', 'per_page': 100, 'page': 2}

        mock_get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues',
            headers=expected_headers,
            params=expected_params_page1,
            timeout=30,
        )
        mock_get.assert_any_call(
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

    @patch('requests.get')
    def test_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = [
            [{'body': 'Comment 1 on issue 1'}, {'body': 'Comment 2 on issue 1'}],
            []
        ]
        mock_get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'
        comments = fetch_comments_for_issue(owner, repository, issue_number)

        assert comments == [{'body': 'Comment 1 on issue 1'}, {'body': 'Comment 2 on issue 1'}]
        assert mock_get.call_count == 2

        expected_headers = {'Authorization': 'token test_token'}
        expected_params_page1 = {'per_page': 100, 'page': 1}
        expected_params_page2 = {'per_page': 100, 'page': 2}

        mock_get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments',
            headers=expected_headers,
            params=expected_params_page1,
            timeout=30,
        )
        mock_get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments',
            headers=expected_headers,
            params=expected_params_page2,
            timeout=30,
        )

    @patch('requests.get')
    def test_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError('500 Server Error')
        mock_get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'

        with pytest.raises(requests.HTTPError) as exc_info:
            fetch_comments_for_issue(owner, repository, issue_number)

        assert str(exc_info.value) == '500 Server Error'

    @patch('requests.get')
    def test_no_comments(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'

        comments = fetch_comments_for_issue(owner, repository, issue_number)
        assert not comments
        mock_get.assert_called_once_with(
            f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments',
            headers={'Authorization': 'token test_token'},
            params={'per_page': 100, 'page': 1},
            timeout=30,
        )

    @patch('requests.get')
    def test_rate_limit_exceeded(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '1234567890'}
        mock_get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'

        with pytest.raises(RateLimitExceededError) as exc_info:
            fetch_comments_for_issue(owner, repository, issue_number)

        assert exc_info.value.reset_time == 1234567890

    @patch('requests.get')
    def test_no_github_token(self, mock_get):
        # Remove the token from the app config
        self.app.config['GITHUB_ACCESS_TOKEN'] = None

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'

        comments = fetch_comments_for_issue(owner, repository, issue_number)
        assert not comments

        mock_get.assert_called_once_with(
            f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments',
            headers={},  # No Authorization header
            params={'per_page': 100, 'page': 1},
            timeout=30,
        )
