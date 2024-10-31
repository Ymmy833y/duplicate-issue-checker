import pytest
import requests
from unittest.mock import MagicMock, patch, call
from werkzeug.datastructures import ImmutableMultiDict
from flask import Flask

from app.logics import (
    get_related_issues, validate_form_data, fetch_issues, 
    fetch_comments_for_issue, get_issues_prs_with_comments, preprocess_text,
    find_related_issues, get_related_issues_detail
)
from app.exceptions import MissingFieldsError, RepositoryNotFoundError

@pytest.fixture
def app_context():
    app = Flask(__name__)
    app.config['GITHUB_ACCESS_TOKEN'] = 'fake_token'
    with app.app_context():
        yield

class TestGetRelatedIssues:
    @patch('app.logics.get_issues_prs_with_comments')
    @patch('app.logics.find_related_issues')
    def test_success(self, mock_find_related_issues, mock_get_issues_prs_with_comments):
        form_data = ImmutableMultiDict({
            'owner': 'test_owner',
            'repository': 'test_repo',
            'title': 'test_title',
            'description': 'test_description'
        })

        mock_get_issues_prs_with_comments.return_value = [
            {'number': 1, 'title': 'issue1', 'url': 'url', 'state': 'open', 'comments': ['comment1', 'comment2']},
            {'number': 2, 'title': 'issue2', 'url': 'url', 'state': 'open', 'comments': ['comment3']},
        ]
        mock_find_related_issues.return_value = [
            {'number': 1, 'title': 'issue1', 'url': 'url', 'state': 'open', 'comments': ['comment1', 'comment2'], 'similarity': float(0.2)},
        ]

        related_issues, related_issues_detail = get_related_issues(form_data)

        mock_get_issues_prs_with_comments.assert_called_once_with('test_owner', 'test_repo')
        mock_find_related_issues.assert_called_once_with('test_title', 'test_description', mock_get_issues_prs_with_comments.return_value)
        
        assert related_issues == [
            {'number': 1, 'title': 'issue1', 'url': 'url', 'state': 'open', 'comments': ['comment1', 'comment2'], 'similarity': float(0.2)},
        ]
        assert related_issues_detail == {
            'total': 1,
            'message': 'There are 1 related issues.'
        }

class TestValidateFormData:
    def test_success(self):
        form_data = ImmutableMultiDict({
            'owner': 'test_owner',
            'repository': 'test_repo',
            'title': 'test_title'
        })
        
        try:
            validate_form_data(form_data)
        except MissingFieldsError:
            pytest.fail('Unexpected MissingFieldsError raised.')

    def test_missing_fields(self):
        form_data = ImmutableMultiDict({
            'owner': 'test_owner',
        })
        with pytest.raises(MissingFieldsError) as excinfo:
            validate_form_data(form_data)
        
        assert excinfo.value.missing_fields == ['repository', 'title']

class TestFetchIssues:
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
            params=expected_params_page1
        )
        mock_get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues',
            headers=expected_headers,
            params=expected_params_page2
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

class TestFetchCommentsForIssue:
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
            [{'id': 1, 'body': 'Comment 1'}],
            []
        ]
        mock_get.return_value = mock_response

        owner = 'test_owner'
        repository = 'test_repo'
        issue_number = '1'
        comments = fetch_comments_for_issue(owner, repository, issue_number)

        assert comments == [{'id': 1, 'body': 'Comment 1'}]
        assert mock_get.call_count == 2

        expected_headers = {'Authorization': 'token test_token'}
        expected_params_page1 = {'per_page': 100, 'page': 1}
        expected_params_page2 = {'per_page': 100, 'page': 2}

        mock_get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments',
            headers=expected_headers,
            params=expected_params_page1
        )
        mock_get.assert_any_call(
            f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments',
            headers=expected_headers,
            params=expected_params_page2
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
        assert comments == []
        mock_get.assert_called_once_with(
            f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments',
            headers={'Authorization': 'token test_token'},
            params={'per_page': 100, 'page': 1}
        )

class TestGetIssuesPRsWithComments:
    @patch('app.logics.fetch_comments_for_issue')
    @patch('app.logics.fetch_issues')
    def test_get_issues_prs_with_comments_success(self, mock_fetch_issues, mock_fetch_comments_for_issue):
        # Mock return value for fetch_issues
        mock_fetch_issues.return_value = [
            {
                'number': 1,
                'title': 'Issue 1',
                'html_url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
                'body': 'Description of issue 1'
            },
            {
                'number': 2,
                'title': 'Issue 2',
                'html_url': 'https://github.com/test_owner/test_repo/issues/2',
                'state': 'closed',
                'body': 'Description of issue 2'
            }
        ]

        # Mock return value for fetch_comments_for_issue
        def fetch_comments_side_effect(owner, repo, issue_number):
            if issue_number == 1:
                return [
                    {'body': 'Comment 1 on issue 1'},
                    {'body': 'Comment 2 on issue 1'}
                ]
            elif issue_number == 2:
                return []  # No comments on Issue 2
            else:
                return []

        mock_fetch_comments_for_issue.side_effect = fetch_comments_side_effect

        owner = 'test_owner'
        repository = 'test_repo'
        issues = get_issues_prs_with_comments(owner, repository)

        expected_issues = [
            {
                'number': 1,
                'title': 'Issue 1',
                'url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'OPEN',
                'comments': [
                    'Description of issue 1',
                    'Comment 1 on issue 1',
                    'Comment 2 on issue 1'
                ]
            },
            {
                'number': 2,
                'title': 'Issue 2',
                'url': 'https://github.com/test_owner/test_repo/issues/2',
                'state': 'CLOSED',
                'comments': [
                    'Description of issue 2'
                ]
            }
        ]

        assert issues == expected_issues

        mock_fetch_issues.assert_called_once_with(owner, repository)
        expected_calls = [
            call(owner, repository, 1),
            call(owner, repository, 2)
        ]
        actual_calls = mock_fetch_comments_for_issue.call_args_list
        assert actual_calls == expected_calls

    @patch('app.logics.fetch_comments_for_issue')
    @patch('app.logics.fetch_issues')
    def test_get_issues_prs_with_comments_no_issues(self, mock_fetch_issues, mock_fetch_comments_for_issue):
        mock_fetch_issues.return_value = []

        owner = 'test_owner'
        repository = 'test_repo'
        issues = get_issues_prs_with_comments(owner, repository)

        assert issues == []

        mock_fetch_issues.assert_called_once_with(owner, repository)
        mock_fetch_comments_for_issue.assert_not_called()

    @patch('app.logics.fetch_comments_for_issue')
    @patch('app.logics.fetch_issues')
    def test_get_issues_prs_with_comments_repository_not_found(self, mock_fetch_issues, mock_fetch_comments_for_issue):
        mock_fetch_issues.side_effect = RepositoryNotFoundError('test_owner', 'test_repo')

        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(RepositoryNotFoundError) as exc_info:
            get_issues_prs_with_comments(owner, repository)

        assert str(exc_info.value) == 'Repository not found: https://github.com/test_owner/test_repo'

        mock_fetch_issues.assert_called_once_with(owner, repository)
        mock_fetch_comments_for_issue.assert_not_called()

    @patch('app.logics.fetch_comments_for_issue')
    @patch('app.logics.fetch_issues')
    def test_get_issues_prs_with_comments_fetch_comments_error(self, mock_fetch_issues, mock_fetch_comments_for_issue):
        mock_fetch_issues.return_value = [
            {
                'number': 1,
                'title': 'Issue 1',
                'html_url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
                'body': 'Description of issue 1'
            }
        ]

        mock_fetch_comments_for_issue.side_effect = requests.HTTPError('Failed to fetch comments')

        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(requests.HTTPError) as exc_info:
            get_issues_prs_with_comments(owner, repository)

        assert str(exc_info.value) == 'Failed to fetch comments'

        mock_fetch_issues.assert_called_once_with(owner, repository)
        mock_fetch_comments_for_issue.assert_called_once_with(owner, repository, 1)

class TestPreprocessText:
    def test_not_text(self):
        input_text = None
        expected_output = ''
        assert preprocess_text(input_text) == expected_output
    
    def test_remove_urls(self):
        input_text = 'Check out this link: http://example.com and https://another.com/page'
        expected_output = 'check out this link and'
        assert preprocess_text(input_text) == expected_output

    def test_remove_mentions(self):
        input_text = 'Hello @user1 and @user2, welcome!'
        expected_output = 'hello and welcome'
        assert preprocess_text(input_text) == expected_output

    def test_remove_hashtags(self):
        input_text = 'This is a #test of the #preprocess_text function.'
        expected_output = 'this is a of the function'
        assert preprocess_text(input_text) == expected_output

    def test_remove_special_characters(self):
        input_text = 'Hello, World! This is a test. #100DaysOfCode @python_dev'
        expected_output = 'hello world this is a test'
        assert preprocess_text(input_text) == expected_output

    def test_multiple_spaces(self):
        input_text = 'This    is  a     test.'
        expected_output = 'this is a test'
        assert preprocess_text(input_text) == expected_output

    def test_already_clean_text(self):
        input_text = 'This text is already clean and has no special elements'
        expected_output = 'this text is already clean and has no special elements'
        assert preprocess_text(input_text) == expected_output

class TestFindRelatedIssues:
    def test_basic(self):
        title = 'Improve login functionality'
        description = 'We need to enhance the login process to support OAuth.'
        issues = [
            {
                'number': 1,
                'title': 'Fix crash on startup',
                'comments': ['The application crashes immediately after launch.', 'App crashes on startup for some users.', 'Investigate the crash logs.'],
                'url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
            },
            {
                'number': 2,
                'title': 'Add support for new OAuth providers',
                'comments': ['We should expand the OAuth support to include more providers.', 'Consider adding support for Facebook and GitHub OAuth.'],
                'url': 'https://github.com/test_owner/test_repo/issues/2',
                'state': 'closed',
            },
            {
                'number': 3,
                'title': 'Update documentation for login',
                'comments': ['The login section in the documentation is outdated.', 'Documentation needs to reflect the new login changes.', 'Add examples for OAuth login.'],
                'url': 'https://github.com/test_owner/test_repo/issues/3',
                'state': 'open',
            },
            {
                'number': 4,
                'title': 'Change the session timeout interval',
                'comments': ['Currently, there is no session validity period, but it will expire after 30 minutes'],
                'url': 'https://github.com/test_owner/test_repo/issues/4',
                'state': 'open',
            }
        ]
        similarity_threshold = 0.2

        related_issues = find_related_issues(title, description, issues, similarity_threshold)

        expected_related_issues = [
            {
                'number': 3,
                'title': 'Update documentation for login',
                'comments': ['The login section in the documentation is outdated.', 'Documentation needs to reflect the new login changes.', 'Add examples for OAuth login.'],
                'url': 'https://github.com/test_owner/test_repo/issues/3',
                'state': 'open',
                'similarity': pytest.approx(0.3, 0.1)
            },
            {
                'number': 2,
                'title': 'Add support for new OAuth providers',
                'comments': ['We should expand the OAuth support to include more providers.', 'Consider adding support for Facebook and GitHub OAuth.'],
                'url': 'https://github.com/test_owner/test_repo/issues/2',
                'state': 'closed',
                'similarity': pytest.approx(0.4, 0.1)
            }
        ]

        assert len(related_issues) == len(expected_related_issues)
        for related, expected in zip(related_issues, expected_related_issues):
            assert related['number'] == expected['number']
            assert related['title'] == expected['title']
            assert related['comments'] == expected['comments']
            assert related['url'] == expected['url']
            assert related['state'] == expected['state']
            assert related['similarity'] >= similarity_threshold

    def test_no_related(self):
        title = 'Implement dark mode'
        description = 'Add a dark mode option to improve user experience in low-light environments.'
        issues = [
            {
                'number': 1,
                'title': 'Fix crash on startup',
                'comments': ['The application crashes immediately after launch.', 'App crashes on startup for some users.', 'Investigate the crash logs.'],
                'url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
            },
            {
                'number': 2,
                'title': 'Improve performance on mobile devices',
                'comments': ['Performance issues on mobile need to be addressed.', 'The app is slow on older mobile devices.', 'Optimize image loading times.'],
                'url': 'https://github.com/test_owner/test_repo/issues/2',
                'state': 'closed',
            }
        ]
        similarity_threshold = 0.2

        related_issues = find_related_issues(title, description, issues, similarity_threshold)

        assert related_issues == []

    def test_threshold_edge(self):
        title = 'Optimize database'
        description = 'Refactor the database schema and optimize queries for better performance.'
        issues = [
            {
                'number': 1,
                'title': 'Database schema refactor',
                'comments': ['The current database schema is not optimized for performance.', 'We need to normalize the database tables.', 'Consider indexing frequently queried fields.'],
                'url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
            },
            {
                'number': 2,
                'title': 'Optimize query performance',
                'comments': ['Improve the performance of database queries.', 'Queries are taking too long to execute.', 'Implement caching for frequent queries.'],
                'url': 'https://github.com/test_owner/test_repo/issues/2',
                'state': 'closed',
            }
        ]
        similarity_threshold = 0.4

        related_issues = find_related_issues(title, description, issues, similarity_threshold)

        for issue in related_issues:
            assert issue['similarity'] >= similarity_threshold

    def test_with_empty_comments(self):
        title = 'Update user profile feature'
        description = 'Enhance the user profile page with new fields and better UI.'
        issues = [
            {
                'number': 1,
                'title': 'Enhance user profile page',
                'comments': [],
                'url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
            }
        ]
        similarity_threshold = 0.2

        related_issues = find_related_issues(title, description, issues, similarity_threshold)

        assert len(related_issues) == len(issues)
        for issue in related_issues:
            assert issue['similarity'] >= similarity_threshold

class TestGetRelatedIssuesDetail:
    def test_with_single_related_issue(self):
        related_issues_len = 1
        expected_output = {
            'total': 1,
            'message': 'There are 1 related issues.'
        }
        assert get_related_issues_detail(related_issues_len) == expected_output

    def test_with_no_related_issues(self):
        related_issues_len = 0
        expected_output = {
            'total': 0,
            'message': 'No related issues found.'
        }
        assert get_related_issues_detail(related_issues_len) == expected_output
