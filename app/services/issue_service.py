import logging
import json
import asyncio

from typing import List
from werkzeug.datastructures import ImmutableMultiDict

from app.services.github_client import fetch_issues, fetch_comments_for_issue
from app.services.issue_searcher import IssueSearcher
from app.schemas.issue_schema import IssueSchema
from app.schemas.issue_detail_schema import IssueDetaiSchema
from app.repositories.issue_repository import IssueRepository
from app.utils.exceptions import RateLimitExceededError, IssueFetchFailedError
from app.utils.validators import validate_form_data

logger = logging.getLogger(__name__)
issue_searcher = IssueSearcher()

async def get_related_issues(form_data: ImmutableMultiDict[str, str]):
    validate_form_data(form_data)

    issues = await get_issues(form_data.get('owner'), form_data.get('repository'))
    logger.debug('issues: %s', issues)

    related_issues = await issue_searcher.find_related_issues(
        issues, form_data.get('title'), form_data.get('description')
    )
    logger.debug('related_issues: %s', related_issues)
    return related_issues, get_related_issues_detail(len(related_issues))

async def get_issues(owner: str, repository: str) -> List[IssueSchema]:
    semaphore = asyncio.Semaphore(5)

    name = generate_issue_name(owner, repository)
    issue_dict = {issue.number: issue for issue in IssueRepository.select_by_name(name)}
    has_rate_limit_exceeded_error = None

    issues = []
    fetch_failed_issues = []

    # Collect tasks to be executed asynchronously
    fetch_comments_tasks = []
    latest_issues_to_fetch_comments_tasks = []

    new_issues = []
    existing_issues = []

    latest_issues = await fetch_issues(owner, repository)
    logger.info('The fetch operation retrieved %d issues.', len(latest_issues))

    for latest_issue in latest_issues:
        number = latest_issue['number']
        updated = latest_issue['updated_at']

        existing_issue = issue_dict.get(number)
        if existing_issue and existing_issue.updated == updated:
            comments_json_str = json.dumps(existing_issue.comments, ensure_ascii=False, indent=2)
            issues.append(IssueSchema(
                name=name,
                number=number,
                title=latest_issue['title'],
                url=latest_issue['html_url'],
                state=latest_issue['state'],
                comments=json.loads(comments_json_str),
                embedding=existing_issue.embedding,
                shape=existing_issue.shape,
                updated=updated
            ))
        else:
            task = fetch_comments_for_issue(semaphore, owner, repository, number)
            fetch_comments_tasks.append(task)
            latest_issues_to_fetch_comments_tasks.append(latest_issue)

    if not fetch_comments_tasks:
        return issues

    logger.info('There are %d issues to retrieve the latest comments.', len(fetch_comments_tasks))
    fetch_results = await asyncio.gather(*fetch_comments_tasks, return_exceptions=True)
    for result, latest_issue in zip(fetch_results, latest_issues_to_fetch_comments_tasks):
        existing_issue = issue_dict.get(latest_issue['number'])
        updated = latest_issue['updated_at']
        if isinstance(result, Exception):
            if isinstance(result, RateLimitExceededError):
                has_rate_limit_exceeded_error = result
                logger.warning(
                    'Processing continues to save successfully retrieved issues to the DB despite an exception'
                )
            else:
                logger.error('%s: - %s', type(result).__name__, result)
                logger.error('Stack trace:', exc_info=True)
            fetch_failed_issues.append(latest_issue['number'])
        else:
            new_issue = await generate_issue_schema(
                owner=owner,
                repository=repository,
                number=latest_issue['number'],
                title=latest_issue['title'],
                url=latest_issue['html_url'],
                state=latest_issue['state'],
                description=latest_issue['body'],
                updated=updated,
                issue_comments=result
            )
            new_issues.append(new_issue)
            if existing_issue:
                existing_issues.append(new_issue.to_issue())

    # Database updates are done in bulk
    if new_issues:
        if existing_issues:
            IssueRepository.delete_all_by_primary_key(existing_issues)
        IssueRepository.bulk_insert([new_issue.to_issue() for new_issue in new_issues])
        issues.extend(new_issues)

    if has_rate_limit_exceeded_error:
        raise has_rate_limit_exceeded_error

    if fetch_failed_issues:
        raise IssueFetchFailedError(fetch_failed_issues)

    return issues

def generate_issue_name(owner: str, repository: str):
    return  f'{owner}/{repository}'

async def generate_issue_schema(
        owner: str, repository: str, number: int, title: str, url: str,
        state: str, description: str, updated: str, issue_comments: list[str]
    ) -> IssueSchema:
    name = generate_issue_name(owner, repository)
    logger.debug('Generate the embedding. name: %s, number: %d', name, number)

    comments = [description] + [comment['body'] for comment in issue_comments]
    embedding, shape = await issue_searcher.generate_serialized_embedding(title, comments)

    return IssueSchema(
        name=name,
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
