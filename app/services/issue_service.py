import logging
import json
from typing import List
from werkzeug.datastructures import ImmutableMultiDict
from app.services.github_client import fetch_issues, fetch_comments_for_issue
from app.services.issue_searcher import IssueSearcher
from app.schemas.issue_schema import IssueSchema
from app.schemas.issue_detail_schema import IssueDetaiSchema
from app.repositories.issue_repository import IssueRepository
from app.utils.validators import validate_form_data

logger = logging.getLogger(__name__)
issue_searcher = IssueSearcher()

def get_related_issues(form_data: ImmutableMultiDict[str, str]):
    validate_form_data(form_data)

    issues = get_issues(form_data.get('owner'), form_data.get('repository'))
    logger.debug('issues: %s', issues)

    related_issues = issue_searcher.find_related_issues(issues, form_data.get('title'), form_data.get('description'))
    logger.debug('related_issues: %s', related_issues)
    return related_issues, get_related_issues_detail(len(related_issues))

def get_issues(owner: str, repository: str) -> List[IssueSchema]:
    name = generate_issue_name(owner, repository)
    issue_dict = {issue.number: issue for issue in IssueRepository.select_by_name(name)}

    issues = []
    for latest_issue in fetch_issues(owner, repository):
        number = latest_issue['number']
        title = latest_issue['title']
        url = latest_issue['html_url']
        state = latest_issue['state']
        updated = latest_issue['updated_at']
        description = latest_issue['body']

        existing_issue = issue_dict.get(number)

        if existing_issue and existing_issue.updated == updated:
            comments_json_str = json.dumps(existing_issue.comments, ensure_ascii=False, indent=2)
            issues.append(IssueSchema(
                name=name,
                number=number,
                title=title,
                url=url,
                state=state,
                comments=json.loads(comments_json_str),
                embedding=existing_issue.embedding,
                shape=existing_issue.shape,
                updated=updated
            ))
        else:
            new_issue = generate_issue_schema(
                owner=owner,
                repository=repository,
                number=number,
                title=title,
                url=url,
                state=state,
                description=description,
                updated=updated
            )
            issues.append(new_issue)

            if existing_issue:
                IssueRepository.update(new_issue.to_issue())
            else:
                IssueRepository.insert(new_issue.to_issue())
    return issues

def generate_issue_name(owner: str, repository: str):
    return  f'{owner}/{repository}'

def generate_issue_schema(
        owner: str, repository: str, number: int, title: str, url: str,
        state: str, description: str, updated: str
    ) -> IssueSchema:
    issue_comments = fetch_comments_for_issue(owner, repository, number)
    comments = [description] + [comment['body'] for comment in issue_comments]

    embedding, shape = issue_searcher.generate_serialized_embedding(title, comments)

    return IssueSchema(
        name=generate_issue_name(owner, repository),
        number=number,
        title=title,
        url=url,
        state=state,
        comments=comments,
        embedding=embedding,
        shape=shape,
        updated=updated,
    )

def get_related_issues_detail(related_issues_len):
    message = f'There are {related_issues_len} related issues.' if related_issues_len else 'No related issues found.'
    return IssueDetaiSchema(
        total=related_issues_len,
        message=message
    )
