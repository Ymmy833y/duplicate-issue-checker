import requests
from flask import current_app
from app.utils.exceptions import RepositoryNotFoundError

def fetch_issues(owner: str, repository: str):
    issues_url = f'https://api.github.com/repos/{owner}/{repository}/issues'
    headers = {'Authorization': f"token {current_app.config.get('GITHUB_ACCESS_TOKEN')}"}

    issues = []
    page = 1
    while True:
        params = {'state': 'all', 'per_page': 100, 'page': page}
        response = requests.get(issues_url, headers=headers, params=params, timeout=30)

        if response.status_code == 404:
            raise RepositoryNotFoundError(owner, repository)

        if response.status_code != 200:
            response.raise_for_status()

        data = response.json()
        if not data:
            break
        issues.extend(data)
        page += 1

    return issues

def fetch_comments_for_issue(owner: str, repository: str, issue_number: str):
    comments_url = f'https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}/comments'
    headers = {'Authorization': f"token {current_app.config.get('GITHUB_ACCESS_TOKEN')}"}

    comments = []
    page = 1

    while True:
        params = {'per_page': 100, 'page': page}
        response = requests.get(comments_url, headers=headers, params=params, timeout=30)

        if response.status_code != 200:
            response.raise_for_status()

        data = response.json()
        if not data:
            break
        comments.extend(data)
        page += 1
    return comments
