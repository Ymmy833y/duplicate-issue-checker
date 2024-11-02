import logging
from werkzeug.datastructures import ImmutableMultiDict
from app.services.github_client import fetch_issues, fetch_comments_for_issue
from app.services.issue_searcher import IssueSearcher
from app.schemas.issue_schema import Issue
from app.utils.validators import validate_form_data

logger = logging.getLogger(__name__)
issue_searcher = IssueSearcher()

def get_related_issues(form_data: ImmutableMultiDict[str, str]):
    validate_form_data(form_data)

    issues = get_issues_prs_with_comments(form_data.get('owner'), form_data.get('repository'))
    logger.debug('issues: %s', issues)

    related_issues = issue_searcher.find_related_issues(issues, form_data.get('title'), form_data.get('description'))
    logger.debug('related_issues: %s', related_issues)
    return related_issues, get_related_issues_detail(len(related_issues))

def get_issues_prs_with_comments(owner: str, repository: str):
    issues = []

    for issue in fetch_issues(owner, repository):
        issue_number = issue['number']
        title = issue['title']
        url = issue['html_url']
        state = issue['state'].upper()
        description = issue['body']

        comments = fetch_comments_for_issue(owner, repository, issue_number)
        comment_texts = [description] + [comment['body'] for comment in comments]

        issues.append(Issue(
            number=issue_number,
            title=title,
            url=url,
            state=state,
            comments=comment_texts,
        ))
    return issues

def get_related_issues_detail(related_issues_len):
    message = f"There are {related_issues_len} related issues." if related_issues_len else "No related issues found."
    return {
        'total': related_issues_len,
        'message': message
    }
