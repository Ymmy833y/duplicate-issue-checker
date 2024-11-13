# pylint: disable=W0621

from unittest.mock import ANY, patch
import pytest

from werkzeug.datastructures import ImmutableMultiDict

from app.services.issue_service import (
    get_related_issues, get_issues, generate_issue_name,
    generate_issue_schema, get_related_issues_detail
)
from app.schemas.display_issue_schema import DisplayIssueSchema
from app.schemas.issue_detail_schema import IssueDetaiSchema
from app.schemas.issue_schema import IssueSchema
from app.models.issue_model import Issue
from app.utils.exceptions import RateLimitExceededError, IssueFetchFailedError

class TestGetRelatedIssues:
    @patch('app.services.issue_service.get_issues')
    @patch('app.services.issue_service.issue_searcher.find_related_issues')
    @pytest.mark.asyncio
    async def test_success(self, mock_find_related_issues, mock_get_issues):
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
                number=1,
                title='issue1',
                url='url',
                state='open',
                comments=['comment1', 'comment2'],
                threshold=0.5
            ),
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

        related_issues, related_issues_detail = await get_related_issues(form_data)

        mock_get_issues.assert_called_once_with('test_owner', 'test_repo')
        mock_find_related_issues.assert_called_once_with(
            mock_get_issues.return_value, 'test_title', 'test_description')

        # Validating sorting
        assert related_issues == [
            DisplayIssueSchema(
                name='test_owner/test_repo',
                number=2,
                title='issue2',
                url='url',
                state='open',
                comments=['comment3'],
                threshold=0.7
            ),
            DisplayIssueSchema(
                name='test_owner/test_repo',
                number=1,
                title='issue1',
                url='url',
                state='open',
                comments=['comment1', 'comment2'],
                threshold=0.5
            )
        ]
        assert related_issues_detail == IssueDetaiSchema(
            total=2,
            message='There are 2 related issues.'
        )

class TestGetIssues:
    def create_issue(
            self, number, name='test_owner/test_repo', comments=None,
            embedding=b'\x00\x01', shape='768', updated='2024-01-01T00:00:00Z'
        ):
        return Issue(
            name=name,
            number=number,
            comments=comments,
            embedding=embedding,
            shape=shape,
            updated=updated
        )

    @pytest.mark.asyncio
    @patch('app.services.issue_service.IssueRepository.bulk_insert')
    @patch('app.services.issue_service.IssueRepository.delete_all_by_primary_key')
    @patch('app.services.issue_service.generate_issue_schema')
    @patch('app.services.issue_service.fetch_comments_for_issue')
    @patch('app.services.issue_service.fetch_issues')
    @patch('app.services.issue_service.IssueRepository.select_by_name')
    async def test_some_issues_updated(
        self, mock_select_by_name, mock_fetch_issues, mock_fetch_comments_for_issue,
        mock_generate_issue_schema, mock_delete_all_by_primary_key, mock_bulk_insert
    ):
        '''
        Testing the case where an existing issue is partially updated
        '''
        existing_issues = [
            self.create_issue(1, updated='2024-01-01T00:00:00Z'),
            self.create_issue(2, updated='2023-10-11T12:34:56Z'),
        ]
        mock_select_by_name.return_value = existing_issues

        mock_fetch_issues.return_value = [
            {
                'number': 1,
                'title': 'Issue 1',
                'html_url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
                'body': 'Updated description of issue 1',
                'updated_at': '2024-01-01T00:00:00Z'  # updated date is same, so should not fetch comments
            },
            {
                'number': 2,
                'title': 'Issue 2',
                'html_url': 'https://github.com/test_owner/test_repo/issues/2',
                'state': 'closed',
                'body': 'Updated description of issue 2',
                'updated_at': '2024-02-01T00:00:00Z'  # updated date is different, so should fetch comments
            }
        ]

        async def fetch_comments_side_effect(_semaphore, _owner, _repo, issue_number):
            if issue_number == 2:
                return [
                    {'body': 'New comment on issue 2'}
                ]
            return []

        mock_fetch_comments_for_issue.side_effect = fetch_comments_side_effect

        async def generate_issue_schema_side_effect(
                owner, repository, number, title, url, state, description, updated, issue_comments
            ):
            comments = ([description] + [comment['body'] for comment in issue_comments])
            return IssueSchema(
                name=f'{owner}/{repository}',
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
        issues = await get_issues(owner, repository)

        expected_issues = [
            IssueSchema(
                name='test_owner/test_repo',
                number=1,
                title='Issue 1',
                url='https://github.com/test_owner/test_repo/issues/1',
                state='open',
                comments=existing_issues[0].comments,
                embedding=existing_issues[0].embedding,
                shape=existing_issues[0].shape,
                updated='2024-01-01T00:00:00Z'
            ),
            IssueSchema(
                name='test_owner/test_repo',
                number=2,
                title='Issue 2',
                url='https://github.com/test_owner/test_repo/issues/2',
                state='closed',
                comments=[
                    'Updated description of issue 2',
                    'New comment on issue 2'
                ],
                embedding=None,
                shape=None,
                updated='2024-02-01T00:00:00Z'
            )
        ]

        assert issues == expected_issues
        mock_select_by_name.assert_called_once_with(f'{owner}/{repository}')
        mock_fetch_issues.assert_called_once_with(owner, repository)
        mock_fetch_comments_for_issue.assert_awaited_once_with(ANY, owner, repository, 2)
        mock_generate_issue_schema.assert_awaited_once()
        mock_bulk_insert.assert_called_once()
        mock_delete_all_by_primary_key.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.services.issue_service.IssueRepository.bulk_insert')
    @patch('app.services.issue_service.IssueRepository.delete_all_by_primary_key')
    @patch('app.services.issue_service.generate_issue_schema')
    @patch('app.services.issue_service.fetch_comments_for_issue')
    @patch('app.services.issue_service.fetch_issues')
    @patch('app.services.issue_service.IssueRepository.select_by_name')
    async def test_success_all_issues_you_have_are_up_to_date(
        self, mock_select_by_name, mock_fetch_issues, mock_fetch_comments_for_issue,
        mock_generate_issue_schema, mock_delete_all_by_primary_key, mock_bulk_insert
    ):
        mock_select_by_name.return_value = [
            self.create_issue(1),
            self.create_issue(2),
        ]
        mock_fetch_issues.return_value = [
            {
                'number': 1,
                'title': 'Issue 1',
                'html_url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
                'body': '',
                'updated_at': '2024-01-01T00:00:00Z'
            },
            {
                'number': 2,
                'title': 'Issue 2',
                'html_url': 'https://github.com/test_owner/test_repo/issues/2',
                'state': 'closed',
                'body': '',
                'updated_at': '2024-01-01T00:00:00Z'
            }
        ]

        owner = 'test_owner'
        repository = 'test_repo'
        issues = await get_issues(owner, repository)

        expected_issues = [
            IssueSchema(
                name='test_owner/test_repo',
                number=1,
                title='Issue 1',
                url='https://github.com/test_owner/test_repo/issues/1',
                state='open',
                comments=None,
                embedding=b'\x00\x01',
                shape='768',
                updated='2024-01-01T00:00:00Z'
            ),
            IssueSchema(
                name='test_owner/test_repo',
                number=2,
                title='Issue 2',
                url='https://github.com/test_owner/test_repo/issues/2',
                state='closed',
                comments=None,
                embedding=b'\x00\x01',
                shape='768',
                updated='2024-01-01T00:00:00Z'
            )
        ]

        assert issues == expected_issues
        mock_select_by_name.assert_called_once_with(f'{owner}/{repository}')
        mock_fetch_issues.assert_called_once_with(owner, repository)
        mock_fetch_comments_for_issue.assert_not_called()
        mock_generate_issue_schema.assert_not_called()
        mock_bulk_insert.assert_not_called()
        mock_delete_all_by_primary_key.assert_not_called()

    @pytest.mark.asyncio
    @patch('app.services.issue_service.IssueRepository.bulk_insert')
    @patch('app.services.issue_service.generate_issue_schema')
    @patch('app.services.issue_service.fetch_comments_for_issue',
        side_effect=RateLimitExceededError(reset_time=1234567890)
    )
    @patch('app.services.issue_service.fetch_issues')
    @patch('app.services.issue_service.IssueRepository.select_by_name')
    async def test_rate_limit_exceeded_error(
        self, mock_select_by_name, mock_fetch_issues, mock_fetch_comments_for_issue,
        mock_generate_issue_schema, mock_bulk_insert
    ):
        mock_select_by_name.return_value = []
        mock_fetch_issues.return_value = [
            {
                'number': 1,
                'title': 'Issue 1',
                'html_url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
                'body': 'Description of issue 1',
                'updated_at': '2024-01-01T00:00:00Z'
            }
        ]

        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(RateLimitExceededError) as exc_info:
            await get_issues(owner, repository)
        assert exc_info.value.reset_time == '2009-02-13 23:31:30'

        mock_fetch_comments_for_issue.assert_awaited_once_with(ANY, owner, repository, 1)
        mock_generate_issue_schema.assert_not_called()
        mock_bulk_insert.assert_not_called()

    @pytest.mark.asyncio
    @patch('app.services.issue_service.IssueRepository.bulk_insert')
    @patch('app.services.issue_service.generate_issue_schema')
    @patch('app.services.issue_service.fetch_comments_for_issue', side_effect=Exception('Fetch error'))
    @patch('app.services.issue_service.fetch_issues')
    @patch('app.services.issue_service.IssueRepository.select_by_name')
    async def test_issue_fetch_failed_error(
        self, mock_select_by_name, mock_fetch_issues, mock_fetch_comments_for_issue,
        mock_generate_issue_schema, mock_bulk_insert
    ):
        mock_select_by_name.return_value = []
        mock_fetch_issues.return_value = [
            {
                'number': 1,
                'title': 'Issue 1',
                'html_url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
                'body': 'Description of issue 1',
                'updated_at': '2024-01-01T00:00:00Z'
            }
        ]


        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(IssueFetchFailedError) as exc_info:
            await get_issues(owner, repository)
        assert exc_info.value.failed_issue_ids == [1]

        mock_fetch_comments_for_issue.assert_awaited_once_with(ANY, owner, repository, 1)
        mock_generate_issue_schema.assert_not_called()
        mock_bulk_insert.assert_not_called()

    @pytest.mark.asyncio
    @patch('app.services.issue_service.fetch_issues', side_effect=Exception('Fetch issues error'))
    @patch('app.services.issue_service.IssueRepository.select_by_name')
    async def test_fetch_issues_exception(
        self, mock_select_by_name, mock_fetch_issues
    ):
        mock_select_by_name.return_value = []

        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(Exception) as exc_info:
            await get_issues(owner, repository)
        assert str(exc_info.value) == 'Fetch issues error'

        mock_fetch_issues.assert_awaited_once_with(owner, repository)
        mock_select_by_name.assert_called_once_with(f'{owner}/{repository}')

    @pytest.mark.asyncio
    @patch('app.services.issue_service.IssueRepository.bulk_insert')
    @patch('app.services.issue_service.generate_issue_schema', side_effect=Exception('Generate issue schema error'))
    @patch('app.services.issue_service.fetch_comments_for_issue')
    @patch('app.services.issue_service.fetch_issues')
    @patch('app.services.issue_service.IssueRepository.select_by_name')
    async def test_generate_issue_schema_exception(
        self, mock_select_by_name, mock_fetch_issues, mock_fetch_comments_for_issue,
        mock_generate_issue_schema, mock_bulk_insert
    ):
        mock_select_by_name.return_value = []
        mock_fetch_issues.return_value = [
            {
                'number': 1,
                'title': 'Issue 1',
                'html_url': 'https://github.com/test_owner/test_repo/issues/1',
                'state': 'open',
                'body': 'Description of issue 1',
                'updated_at': '2024-01-01T00:00:00Z'
            }
        ]

        mock_fetch_comments_for_issue.return_value = [
            {'body': 'Comment on issue 1'}
        ]

        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(Exception) as exc_info:
            await get_issues(owner, repository)
        assert str(exc_info.value) == 'Generate issue schema error'

        mock_fetch_comments_for_issue.assert_awaited_once_with(ANY, owner, repository, 1)
        mock_generate_issue_schema.assert_awaited_once()
        mock_bulk_insert.assert_not_called()

class TestGenerateIssueName:
    def test_success(self):
        result = generate_issue_name('test_owner', 'test_repo')
        assert result == 'test_owner/test_repo'

class TestGenerateIssueSchema():
    @pytest.mark.asyncio
    @patch('app.services.issue_service.issue_searcher.generate_serialized_embedding')
    async def test_success(self, mock_generate_serialized_embedding):
        mock_generate_serialized_embedding.return_value = (b'fake_embedding_bytes', '768')

        owner = 'test_owner'
        repository = 'test_repo'
        number = 1
        title = 'Test Issue Title'
        url = 'https://github.com/test_owner/test_repo/issues/1'
        state = 'open'
        description = 'This is a test issue description.'
        updated = '2024-01-01T00:00:00Z'
        issue_comments = [
            {'body': 'Comment 1 on issue'},
            {'body': 'Comment 2 on issue'}
        ]

        result = await generate_issue_schema(
            owner, repository, number, title, url, state, description, updated, issue_comments
        )

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
        mock_generate_serialized_embedding.assert_called_once_with(
            title, [description, 'Comment 1 on issue', 'Comment 2 on issue']
        )

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
