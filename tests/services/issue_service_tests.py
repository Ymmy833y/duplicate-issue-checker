# pylint: disable=W0621

from unittest.mock import patch
from werkzeug.datastructures import ImmutableMultiDict

from app.services.issue_service import (
    get_related_issues, get_issues, generate_issue_name,
    generate_issue_schema, get_related_issues_detail
)
from app.schemas.display_issue_schema import DisplayIssueSchema
from app.schemas.issue_detail_schema import IssueDetaiSchema
from app.schemas.issue_schema import IssueSchema

class TestGetRelatedIssues:
    @patch('app.services.issue_service.get_issues')
    @patch('app.services.issue_service.issue_searcher.find_related_issues')
    def test_success(self, mock_find_related_issues, mock_get_issues):
        form_data = ImmutableMultiDict({
            'owner': 'test_owner',
            'repository': 'test_repo',
            'title': 'test_title',
            'description': 'test_description'
        })

        mock_get_issues.return_value = [
            IssueSchema(
                name='test_owner/test_repo',
                number=1,
                title='issue1',
                url='url',
                state='open',
                comments=['comment1', 'comment2'],
                embedding=b'\x00\x01\x02\x03\x04\x05\x06\x07',
                shape='768',
                updated='2024-01-01'
            ),
            IssueSchema(
                name='test_owner/test_repo',
                number=2,
                title='issue2',
                url='url',
                state='open',
                comments=['comment3'],
                embedding=b'\x89PNG\r\n\x1a\n',
                shape='768',
                updated='2024-01-01'
            )
        ]
        mock_find_related_issues.return_value = [
            DisplayIssueSchema(
                name='test_owner/test_repo',
                number=2,
                title='issue2',
                url='url',
                state='open',
                comments=['comment3'],
                threshold=0.7
            )
        ]

        related_issues, related_issues_detail = get_related_issues(form_data)

        mock_get_issues.assert_called_once_with('test_owner', 'test_repo')
        mock_find_related_issues.assert_called_once_with(
            mock_get_issues.return_value, 'test_title', 'test_description')

        assert related_issues == [
            DisplayIssueSchema(
                name='test_owner/test_repo',
                number=2,
                title='issue2',
                url='url',
                state='open',
                comments=['comment3'],
                threshold=0.7
            )
        ]
        assert related_issues_detail == IssueDetaiSchema(
            total=1,
            message='There are 1 related issues.'
        )

class TestGetIssues:
    @patch('app.services.issue_service.IssueRepository.insert')
    @patch('app.services.issue_service.IssueRepository.update')
    @patch('app.services.issue_service.generate_issue_schema')
    @patch('app.services.issue_service.IssueRepository.select_by_name')
    @patch('app.services.issue_service.fetch_comments_for_issue')
    @patch('app.services.issue_service.fetch_issues')
    def test_success(
        self, mock_fetch_issues, mock_fetch_comments_for_issue, mock_select_by_name,
        mock_generate_issue_schema, mock_update, mock_insert
    ):

        mock_fetch_issues.return_value = [
            {
                'number': 1,
                'title': 'Issue 1',
                'html_url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
                'body': 'Description of issue 1',
                'updated_at': '2024-01-01T00:00:00Z'
            },
            {
                'number': 2,
                'title': 'Issue 2',
                'html_url': 'https://github.com/test_owner/test_repo/issues/2',
                'state': 'closed',
                'body': 'Description of issue 2',
                'updated_at': '2023-10-11T12:34:56Z'
            }
        ]

        # Mock return value for fetch_comments_for_issue
        def fetch_comments_side_effect(_owner, _repo, issue_number):
            if issue_number == 1:
                return [
                    {'body': 'Comment 1 on issue 1'},
                    {'body': 'Comment 2 on issue 1'}
                ]
            if issue_number == 2:
                return []
            return []

        mock_fetch_comments_for_issue.side_effect = fetch_comments_side_effect

        # Mock configuration for IssueRepository.select_by_name (no existing issues)
        mock_select_by_name.return_value = []

        # pylint: disable=R0801
        def generate_issue_schema_side_effect(
                owner, repository, number, title, url, state, description, updated
            ):
            comments = ([description]
                + [comment['body'] for comment in fetch_comments_side_effect(owner, repository, number)])
            return IssueSchema(
                name=f"{owner}/{repository}",
                number=number,
                title=title,
                url=url,
                state=state,
                comments=comments,
                embedding=None,
                shape=None,
                updated=updated
            )

        mock_generate_issue_schema.side_effect = generate_issue_schema_side_effect

        owner = 'test_owner'
        repository = 'test_repo'

        issues = get_issues(owner, repository)

        expected_issues = [
            IssueSchema(
                name='test_owner/test_repo',
                number=1,
                title='Issue 1',
                url='https://github.com/test_owner/test_repo/issues/1',
                state='open',
                comments=[
                    'Description of issue 1',
                    'Comment 1 on issue 1',
                    'Comment 2 on issue 1'
                ],
                embedding=None,
                shape=None,
                updated='2024-01-01T00:00:00Z'
            ),
            IssueSchema(
                name='test_owner/test_repo',
                number=2,
                title='Issue 2',
                url='https://github.com/test_owner/test_repo/issues/2',
                state='closed',
                comments=[
                    'Description of issue 2'
                ],
                embedding=None,
                shape=None,
                updated='2023-10-11T12:34:56Z'
            )
        ]

        assert issues == expected_issues

        mock_fetch_issues.assert_called_once_with(owner, repository)
        mock_select_by_name.assert_called_once_with(f"{owner}/{repository}")
        assert mock_generate_issue_schema.call_count == 2
        assert mock_insert.call_count == 2
        mock_update.assert_not_called()

    @patch('app.services.issue_service.IssueRepository.insert')
    @patch('app.services.issue_service.IssueRepository.update')
    @patch('app.services.issue_service.generate_issue_schema')
    @patch('app.services.issue_service.IssueRepository.select_by_name')
    @patch('app.services.issue_service.fetch_comments_for_issue')
    @patch('app.services.issue_service.fetch_issues')
    def test_existing_issues(
        self, mock_fetch_issues, mock_fetch_comments_for_issue, mock_select_by_name,
        mock_generate_issue_schema, mock_update, mock_insert
    ):

        mock_fetch_issues.return_value = [
            {
                'number': 1,
                'title': 'Issue 1',
                'html_url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
                'body': 'Description of issue 1',
                'updated_at': '2024-02-02T00:00:00Z'
            },
            {
                'number': 2,
                'title': 'Issue 2',
                'html_url': 'https://github.com/test_owner/test_repo/issues/2',
                'state': 'open',
                'body': 'Description of issue 2',
                'updated_at': '2024-01-01T00:00:00Z'
            }
        ]

        mock_fetch_comments_for_issue.return_value = [
            {'body': 'Comment on issue 1'}
        ]

        # Mock configuration when existing issues exist in the repository
        mock_select_by_name.return_value = [
            IssueSchema(
                name='test_owner/test_repo',
                number=1,
                title='Issue 1',
                url='https://github.com/test_owner/test_repo/issues/1',
                state='open',
                comments=[
                    'Old description of issue 1',
                    'Old comment on issue 1'
                ],
                embedding=None,
                shape=None,
                updated='2024-01-01T00:00:00Z'  # Old updated
            ),
            IssueSchema(
                name='test_owner/test_repo',
                number=2,
                title='Issue 2',
                url='https://github.com/test_owner/test_repo/issues/2',
                state='open',
                comments=[
                    'Description of issue 2',
                    'Comment on issue 2'
                ],
                embedding=None,
                shape=None,
                updated='2024-01-01T00:00:00Z'
            )
        ]

        # pylint: disable=R0801
        def generate_issue_schema_side_effect(
                owner, repository, number, title, url, state, description, updated
            ):
            comments = [description] + [comment['body'] for comment in mock_fetch_comments_for_issue.return_value]
            return IssueSchema(
                name=f"{owner}/{repository}",
                number=number,
                title=title,
                url=url,
                state=state,
                comments=comments,
                embedding=None,
                shape=None,
                updated=updated
            )

        mock_generate_issue_schema.side_effect = generate_issue_schema_side_effect

        owner = 'test_owner'
        repository = 'test_repo'

        issues = get_issues(owner, repository)

        # Verify that the updated issue is returned
        expected_issue = [
            IssueSchema(
                name='test_owner/test_repo',
                number=1,
                title='Issue 1',
                url='https://github.com/test_owner/test_repo/issues/1',
                state='open',
                comments=[
                    'Description of issue 1',
                    'Comment on issue 1'
                ],
                embedding=None,
                shape=None,
                updated='2024-02-02T00:00:00Z'
            ),
            IssueSchema(
                name='test_owner/test_repo',
                number=2,
                title='Issue 2',
                url='https://github.com/test_owner/test_repo/issues/2',
                state='open',
                comments=[
                    'Description of issue 2',
                    'Comment on issue 2'
                ],
                embedding=None,
                shape=None,
                updated='2024-01-01T00:00:00Z'
            )
        ]

        issues_as_dicts = [issue.__dict__ for issue in issues]
        expected_issue_as_dicts = [issue.__dict__ for issue in expected_issue]
        assert issues_as_dicts == expected_issue_as_dicts
        mock_update.assert_called_once()
        mock_insert.assert_not_called()

    @patch('app.services.issue_service.IssueRepository.insert')
    @patch('app.services.issue_service.IssueRepository.update')
    @patch('app.services.issue_service.generate_issue_schema')
    @patch('app.services.issue_service.IssueRepository.select_by_name')
    @patch('app.services.issue_service.fetch_comments_for_issue')
    @patch('app.services.issue_service.fetch_issues')
    def test_no_issues_returned(
        self, mock_fetch_issues, mock_fetch_comments_for_issue, mock_select_by_name,
        mock_generate_issue_schema, mock_update, mock_insert
    ):

        # fetch_issues returns an empty list
        mock_fetch_issues.return_value = []

        mock_select_by_name.return_value = []

        owner = 'test_owner'
        repository = 'test_repo'

        issues = get_issues(owner, repository)

        assert not issues
        mock_fetch_issues.assert_called_once_with(owner, repository)
        mock_select_by_name.assert_called_once_with(f"{owner}/{repository}")
        mock_fetch_comments_for_issue.assert_not_called()
        mock_generate_issue_schema.assert_not_called()
        mock_insert.assert_not_called()
        mock_update.assert_not_called()

class TestGenerateIssueName:
    def test_success(self):
        result = generate_issue_name('test_owner', 'test_repo')
        assert result == 'test_owner/test_repo'

class TestGenerateIssueSchema():
    @patch('app.services.issue_service.fetch_comments_for_issue')
    @patch('app.services.issue_service.issue_searcher.generate_serialized_embedding')
    def test_success(self, mock_generate_serialized_embedding, mock_fetch_comments_for_issue):
        mock_fetch_comments_for_issue.return_value = [
            {'body': 'Comment 1 on issue'},
            {'body': 'Comment 2 on issue'}
        ]
        mock_generate_serialized_embedding.return_value = (b'fake_embedding_bytes', '768')

        owner = 'test_owner'
        repository = 'test_repo'
        number = 1
        title = 'Test Issue Title'
        url = 'https://github.com/test_owner/test_repo/issues/1'
        state = 'open'
        description = 'This is a test issue description.'
        updated = '2024-01-01T00:00:00Z'

        result = generate_issue_schema(owner, repository, number, title, url, state, description, updated)

        expected_issue_schema = IssueSchema(
            name='test_owner/test_repo',
            number=number,
            title=title,
            url=url,
            state=state,
            comments=[
                description,
                'Comment 1 on issue',
                'Comment 2 on issue'
            ],
            embedding=b'fake_embedding_bytes',
            shape='768',
            updated=updated
        )

        assert result == expected_issue_schema
        mock_fetch_comments_for_issue.assert_called_once_with(owner, repository, number)
        mock_generate_serialized_embedding.assert_called_once_with(
            title, [description, 'Comment 1 on issue', 'Comment 2 on issue']
        )

    @patch('app.services.issue_service.fetch_comments_for_issue')
    @patch('app.services.issue_service.issue_searcher.generate_serialized_embedding')
    def test_success_with_no_comments(self, mock_generate_serialized_embedding, mock_fetch_comments_for_issue):
        mock_fetch_comments_for_issue.return_value = []
        mock_generate_serialized_embedding.return_value = (b'fake_embedding_bytes', '768')

        owner = 'test_owner'
        repository = 'test_repo'
        number = 1
        title = 'Test Issue Title'
        url = 'https://github.com/test_owner/test_repo/issues/1'
        state = 'open'
        description = 'This is a test issue description.'
        updated = '2024-01-01T00:00:00Z'

        result = generate_issue_schema(owner, repository, number, title, url, state, description, updated)

        expected_issue_schema = IssueSchema(
            name='test_owner/test_repo',
            number=number,
            title=title,
            url=url,
            state=state,
            comments=[
                description
            ],
            embedding=b'fake_embedding_bytes',
            shape='768',
            updated=updated
        )

        assert result == expected_issue_schema
        mock_fetch_comments_for_issue.assert_called_once_with(owner, repository, number)
        mock_generate_serialized_embedding.assert_called_once_with(title, [description])

class TestGetRelatedIssuesDetail:
    def test_with_single_related_issue(self):
        related_issues_len = 1
        expected_output = IssueDetaiSchema(
            total=1,
            message='There are 1 related issues.'
        )
        assert get_related_issues_detail(related_issues_len) == expected_output

    def test_with_no_related_issues(self):
        related_issues_len = 0
        expected_output = IssueDetaiSchema(
            total=0,
            message='No related issues found.'
        )
        assert get_related_issues_detail(related_issues_len) == expected_output
