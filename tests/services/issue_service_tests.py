# pylint: disable=W0621

from unittest.mock import patch, call

import pytest
import requests
from werkzeug.datastructures import ImmutableMultiDict

from app.services.issue_service import (
    get_related_issues, get_issues_prs_with_comments, get_related_issues_detail
)
from app.schemas.issue_schema import Issue
from app.utils.exceptions import RepositoryNotFoundError

class TestGetRelatedIssues:
    @patch('app.services.issue_service.get_issues_prs_with_comments')
    @patch('app.services.issue_service.issue_searcher.find_related_issues')
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
            {
                'number': 1, 'title': 'issue1', 'url': 'url', 'state': 'open',
                'comments': ['comment1', 'comment2'], 'similarity': 0.2
            },
        ]

        related_issues, related_issues_detail = get_related_issues(form_data)

        mock_get_issues_prs_with_comments.assert_called_once_with('test_owner', 'test_repo')
        mock_find_related_issues.assert_called_once_with(
            mock_get_issues_prs_with_comments.return_value, 'test_title', 'test_description')

        assert related_issues == [
            {
                'number': 1, 'title': 'issue1', 'url': 'url', 'state': 'open',
                'comments': ['comment1', 'comment2'], 'similarity': 0.2
            },
        ]
        assert related_issues_detail == {
            'total': 1,
            'message': 'There are 1 related issues.'
        }

class TestGetIssuesPRsWithComments:
    @patch('app.services.issue_service.fetch_comments_for_issue')
    @patch('app.services.issue_service.fetch_issues')
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
        def fetch_comments_side_effect(_owner, _repo, issue_number):
            if issue_number == 1:
                return [
                    {'body': 'Comment 1 on issue 1'},
                    {'body': 'Comment 2 on issue 1'}
                ]
            if issue_number == 2:
                return []  # No comments on Issue 2
            return []

        mock_fetch_comments_for_issue.side_effect = fetch_comments_side_effect

        owner = 'test_owner'
        repository = 'test_repo'
        issues = get_issues_prs_with_comments(owner, repository)

        expected_issues = [
            Issue(
                number=1,
                title='Issue 1',
                url='https://github.com/test_owner/test_repo/issues/1',
                state='OPEN',
                comments=[
                    'Description of issue 1',
                    'Comment 1 on issue 1',
                    'Comment 2 on issue 1'
                ]
            ),
            Issue(
                number=2,
                title='Issue 2',
                url='https://github.com/test_owner/test_repo/issues/2',
                state='CLOSED',
                comments=[
                    'Description of issue 2'
                ]
            )
        ]

        assert issues == expected_issues

        mock_fetch_issues.assert_called_once_with(owner, repository)
        expected_calls = [
            call(owner, repository, 1),
            call(owner, repository, 2)
        ]
        actual_calls = mock_fetch_comments_for_issue.call_args_list
        assert actual_calls == expected_calls

    @patch('app.services.issue_service.fetch_comments_for_issue')
    @patch('app.services.issue_service.fetch_issues')
    def test_get_issues_prs_with_comments_no_issues(self, mock_fetch_issues, mock_fetch_comments_for_issue):
        mock_fetch_issues.return_value = []

        owner = 'test_owner'
        repository = 'test_repo'
        issues = get_issues_prs_with_comments(owner, repository)

        assert not issues

        mock_fetch_issues.assert_called_once_with(owner, repository)
        mock_fetch_comments_for_issue.assert_not_called()

    @patch('app.services.issue_service.fetch_comments_for_issue')
    @patch('app.services.issue_service.fetch_issues')
    def test_get_issues_prs_with_comments_repository_not_found(self, mock_fetch_issues, mock_fetch_comments_for_issue):
        mock_fetch_issues.side_effect = RepositoryNotFoundError('test_owner', 'test_repo')

        owner = 'test_owner'
        repository = 'test_repo'

        with pytest.raises(RepositoryNotFoundError) as exc_info:
            get_issues_prs_with_comments(owner, repository)

        assert str(exc_info.value) == 'Repository not found: https://github.com/test_owner/test_repo'

        mock_fetch_issues.assert_called_once_with(owner, repository)
        mock_fetch_comments_for_issue.assert_not_called()

    @patch('app.services.issue_service.fetch_comments_for_issue')
    @patch('app.services.issue_service.fetch_issues')
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
