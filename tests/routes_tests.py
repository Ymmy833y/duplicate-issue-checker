# pylint: disable=W0621

from unittest.mock import patch
import pytest
from flask import template_rendered
from app import create_app
from app.utils.exceptions import (
    MissingFieldsError, RepositoryNotFoundError,
    RateLimitExceededError, UnauthorizedError
)

from tests.testing_config import TestingConfig

@pytest.fixture
def test_app():
    app = create_app(TestingConfig)
    return app

@pytest.fixture
def client(test_app):
    return test_app.test_client()

@pytest.fixture
def captured_templates(test_app):
    recorded = []

    def record(_sender, template, context, **_extra):
        recorded.append((template, context))

    template_rendered.connect(record, test_app)
    yield recorded
    template_rendered.disconnect(record, test_app)

class TestIndex:
    def test_include_session_data(self, client, captured_templates):
        with client.session_transaction() as sess:
            sess['form_data'] = {
                'owner': 'test_owner',
                'repository': 'test_repository',
                'title': 'test_title'
            }
            sess['error_message'] = 'test_error_message'

        response = client.get('/')

        assert response.status_code == 200

        assert len(captured_templates) == 1
        template, context = captured_templates[0]
        assert template.name == 'index.html'
        assert context['form_data'] == {
            'owner': 'test_owner',
            'repository': 'test_repository',
            'title': 'test_title'
        }
        assert context['error_message'] == 'test_error_message'

        with client.session_transaction() as sess:
            assert 'form_data' not in sess
            assert 'error_message' not in sess

    def test_without_session_data(self, client, captured_templates):
        response = client.get('/')

        assert response.status_code == 200

        assert len(captured_templates) == 1
        template, context = captured_templates[0]
        assert template.name == 'index.html'
        assert context['form_data'] == {}
        assert context['error_message'] is None

class TestSearch:
    @patch('app.routes.get_related_issues')
    def test_success(self, mock_get_related_issues, client):
        form_data = {
            'owner': 'test_owner',
            'repository': 'test_repository',
            'title': 'test_title'
        }
        expected_issues = [{
            'number': 1,
            'title': 'issue1',
            'url': 'http://example.com/1',
            'state': 'open',
            'comments': ['comment1'],
            'threshold': 0.7,
        }]
        expected_detail = {'total': 1, 'message': 'Found 1 issue'}

        mock_get_related_issues.return_value = (expected_issues, expected_detail)

        response = client.post('/search', data=form_data, follow_redirects=False)

        assert response.status_code == 200
        assert b'Found 1 issue' in response.data

    @patch('app.routes.get_related_issues')
    def test_missing_fields_error(self, mock_get_related_issues, client):
        form_data = {
            'owner': '',
            'repository': 'test_repository',
            'title': 'test_title'
        }
        mock_get_related_issues.side_effect = MissingFieldsError(['owner'])

        response = client.post('/search', data=form_data, follow_redirects=False)

        assert response.status_code == 302
        assert response.headers['Location'] == '/'

        with client.session_transaction() as sess:
            assert sess['form_data'] == form_data
            assert 'issues' not in sess
            assert 'detail' not in sess
            assert sess['error_message'] == 'Missing fields: owner'

    @patch('app.routes.get_related_issues')
    def test_repository_not_found_error(self, mock_get_related_issues, client):
        form_data = {
            'owner': 'test_owner',
            'repository': 'nonexistent_repo',
            'title': 'test_title'
        }
        mock_get_related_issues.side_effect = RepositoryNotFoundError(
            'test_owner', 'nonexistent_repo'
        )

        response = client.post('/search', data=form_data, follow_redirects=False)

        assert response.status_code == 302
        assert response.headers['Location'] == '/'

        with client.session_transaction() as sess:
            assert sess['form_data'] == form_data
            assert 'issues' not in sess
            assert 'detail' not in sess
            assert sess['error_message'] == (
                'Repository not found: https://github.com/test_owner/nonexistent_repo'
            )

    @patch('app.routes.get_related_issues')
    def test_rate_limit_error(self, mock_get_related_issues, client):
        form_data = {
            'owner': 'test_owner',
            'repository': 'test_repo',
            'title': 'test_title'
        }
        mock_get_related_issues.side_effect = RateLimitExceededError(
            reset_time=1234567890
        )

        response = client.post('/search', data=form_data, follow_redirects=False)

        assert response.status_code == 302
        assert response.headers['Location'] == '/'

        with client.session_transaction() as sess:
            assert sess['form_data'] == form_data
            assert 'issues' not in sess
            assert 'detail' not in sess
            assert sess['error_message'] == (
                'Rate limit exceeded. Try again after 2009-02-13 23:31:30 (UTC)'
            )

    @patch('app.routes.get_related_issues')
    def test_unauthorized_error(self, mock_get_related_issues, client):
        form_data = {
            'owner': 'test_owner',
            'repository': 'test_repo',
            'title': 'test_title'
        }
        mock_get_related_issues.side_effect = UnauthorizedError()

        response = client.post('/search', data=form_data, follow_redirects=False)

        assert response.status_code == 302
        assert response.headers['Location'] == '/'

        with client.session_transaction() as sess:
            assert sess['form_data'] == form_data
            assert 'issues' not in sess
            assert 'detail' not in sess
            assert sess['error_message'] == (
                'Unauthorized access. Please check your GITHUB_ACCESS_TOKEN'
            )

    @patch('app.routes.get_related_issues')
    def test_unexpected_exception(self, mock_get_related_issues, client):
        form_data = {
            'owner': 'test_owner',
            'repository': 'test_repository',
            'title': 'test_title'
        }
        mock_get_related_issues.side_effect = Exception()

        response = client.post('/search', data=form_data, follow_redirects=False)

        assert response.status_code == 302
        assert response.headers['Location'] == '/'

        with client.session_transaction() as sess:
            assert sess['form_data'] == form_data
            assert 'issues' not in sess
            assert 'detail' not in sess
            assert sess['error_message'] == (
                'An unexpected error occurred. Please try again.'
            )
