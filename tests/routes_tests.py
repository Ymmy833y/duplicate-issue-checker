import pytest
from flask import template_rendered
from unittest.mock import patch
from app import create_app
from app.exceptions import MissingFieldsError, RepositoryNotFoundError

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def captured_templates(app):
    recorded = []

    def record(sender, template, context, **extra):
        recorded.append((template, context))

    template_rendered.connect(record, app)
    yield recorded
    template_rendered.disconnect(record, app)

class TestIndex:
    def test_include_session_data(self, client, captured_templates):
        with client.session_transaction() as sess:
            sess['form_data'] = {'owner': 'test_owner', 'repository': 'test_repository', 'title': 'test_title'}
            sess['issues'] = [{'number': 1, 'title': 'test_title', 'url': 'test_url', 'state': 'test_state', 'comments': ['test_comment']}]
            sess['detail'] = {'total': 1, 'message': 'test_message'}
            sess['error_message'] = 'test_error_message'

        response = client.get('/')

        assert response.status_code == 200

        assert len(captured_templates) == 1
        template, context = captured_templates[0]
        assert template.name == 'index.html'
        assert context['form_data'] == {'owner': 'test_owner', 'repository': 'test_repository', 'title': 'test_title'}
        assert context['issues'] == [{'number': 1, 'title': 'test_title', 'url': 'test_url', 'state': 'test_state', 'comments': ['test_comment']}]
        assert context['detail'] == {'total': 1, 'message': 'test_message'}
        assert context['error_message'] == 'test_error_message'

        with client.session_transaction() as sess:
            assert 'form_data' not in sess
            assert 'issues' not in sess
            assert 'detail' not in sess
            assert 'error_message' not in sess

    def test_without_session_data(self, client, captured_templates):
        response = client.get('/')

        assert response.status_code == 200

        assert len(captured_templates) == 1
        template, context = captured_templates[0]
        assert template.name == 'index.html'
        assert context['form_data'] == {}
        assert context['issues'] == []
        assert context['detail'] == {}
        assert context['error_message'] is None

class TestSearch:
    @patch('app.routes.get_related_issues')
    def test_search_success(self, mock_get_related_issues, client):
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
            'comments': ['comment1']
        }]
        expected_detail = {'total': 1, 'message': 'Found 1 issue'}

        mock_get_related_issues.return_value = (expected_issues, expected_detail)

        response = client.post('/search', data=form_data, follow_redirects=False)

        assert response.status_code == 302
        assert response.headers['Location'] == '/'

        with client.session_transaction() as sess:
            assert sess['form_data'] == form_data
            assert sess['issues'] == expected_issues
            assert sess['detail'] == expected_detail
            assert 'error_message' not in sess

    @patch('app.routes.get_related_issues')
    def test_search_missing_fields_error(self, mock_get_related_issues, client):
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
    def test_search_repository_not_found_error(self, mock_get_related_issues, client):
        form_data = {
            'owner': 'test_owner',
            'repository': 'nonexistent_repo',
            'title': 'test_title'
        }
        mock_get_related_issues.side_effect = RepositoryNotFoundError('test_owner', 'nonexistent_repo')

        response = client.post('/search', data=form_data, follow_redirects=False)

        assert response.status_code == 302
        assert response.headers['Location'] == '/'

        with client.session_transaction() as sess:
            assert sess['form_data'] == form_data
            assert 'issues' not in sess
            assert 'detail' not in sess
            assert sess['error_message'] == 'Repository not found: https://github.com/test_owner/nonexistent_repo'

    @patch('app.routes.get_related_issues')
    def test_search_unexpected_exception(self, mock_get_related_issues, client):
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
            assert sess['error_message'] == 'An unexpected error occurred. Please try again.'
