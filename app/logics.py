import requests
import re
import logging
from flask import current_app
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.datastructures import ImmutableMultiDict
from .exceptions import MissingFieldsError, RepositoryNotFoundError

logger = logging.getLogger(__name__)

def get_related_issues(form_data: ImmutableMultiDict[str, str]):
    validate_form_data(form_data)

    issues = get_issues_prs_with_comments(form_data.get('owner'), form_data.get('repository'))
    logger.debug(f'issues: {issues}')

    related_issues = find_related_issues(form_data.get('title'), form_data.get('description'), issues)
    logger.debug(f'related_issues: {related_issues}')
    return related_issues, get_related_issues_detail(len(related_issues))

def validate_form_data(form_data: ImmutableMultiDict[str, str]):
    missing_fields = []
    required_fields = ['owner', 'repository', 'title']
    
    for field in required_fields:
        value = form_data.get(field)
        if not value:
            missing_fields.append(field)
    
    if missing_fields:
        raise MissingFieldsError(missing_fields)

def fetch_issues(owner: str, repository: str):
    issues_url = f'https://api.github.com/repos/{owner}/{repository}/issues'
    headers = {'Authorization': f"token {current_app.config.get('GITHUB_ACCESS_TOKEN')}"}

    issues = []
    page = 1
    while True:
        params = {'state': 'all', 'per_page': 100, 'page': page}
        response = requests.get(issues_url, headers=headers, params=params)

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
        response = requests.get(comments_url, headers=headers, params=params)
        
        if response.status_code != 200:
            response.raise_for_status()
        
        data = response.json()
        if not data:
            break
        comments.extend(data)
        page += 1
    return comments

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
        
        issues.append({
            'number': issue_number,
            'title': title,
            'url': url,
            'state': state,
            'comments': comment_texts
        })
    return issues

def preprocess_text(text: str):
    if not text:
        return ''
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#\S+', '', text)
    text = re.sub(r'[^A-Za-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = text.lower()
    return text

def find_related_issues(title: str, description: str, issues, similarity_threshold=0.2):
    issue_texts = []
    issue_ids = []
    issue_data = []
    for issue in issues:
        combined_text = issue.get('title') + ' ' + ' '.join(filter(None, map(str, issue.get('comments', []))))
        issue_texts.append(preprocess_text(combined_text))
        issue_ids.append(issue.get('number'))
        issue_data.append(issue)

    corpus = issue_texts + [preprocess_text(f'title: {title}, description: {description}')]
    logger.debug(f'corpus: {corpus}')

    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(corpus)

    search_vector = tfidf_matrix[-1]
    issue_vectors = tfidf_matrix[:-1]

    similarities = cosine_similarity(search_vector, issue_vectors).flatten()

    similar_indices = [i for i, score in enumerate(similarities) if score >= similarity_threshold]
    similar_scores = similarities[similar_indices]

    sorted_indices = [x for _, x in sorted(zip(similar_scores, similar_indices), reverse=True)]
    sorted_scores = sorted(similar_scores, reverse=True)

    related_issues = []
    for idx, score in zip(sorted_indices, sorted_scores):
        issue = issue_data[idx]
        issue['similarity'] = score
        related_issues.append(issue)

    return related_issues

def get_related_issues_detail(related_issues_len):
    message = f'There are {related_issues_len} related issues.' if related_issues_len > 0 else 'No related issues found.'
    return {
        'total': related_issues_len,
        'message': message
    }
