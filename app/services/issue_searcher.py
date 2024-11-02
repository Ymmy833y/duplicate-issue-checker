import re
from typing import List
from sentence_transformers import SentenceTransformer, util
from app.schemas.issue_schema import Issue

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

class IssueSearcher:
    def __init__(self, model_name: str = 'paraphrase-mpnet-base-v2', threshold: float = 0.5):
        """
        Initialize the SBERT model and set the similarity threshold.
        """
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold

    def set_threshold(self, threshold: float):
        """
        Update the similarity threshold.
        """
        self.threshold = threshold

    def find_related_issues(self, issues: List[Issue], title: str, description: str):
        """
        Find issue comments that are semantically similar to the search query using SBERT.

        :param issue_comments: List of issue comments to search within
        :param title: Search query
        :param description: Search query
        :return: List of comments and similarity scores that exceed the threshold
        """
        # Preprocessing an Issues
        comments = [preprocess_text(f"{issue.title}: {' '.join(issue.comments)}") for issue in issues]

        # Encode the search query and issue comments
        search_embedding = self.model.encode(preprocess_text(f'{title}: {description}'), convert_to_tensor=True)
        comments_embeddings = self.model.encode(comments, convert_to_tensor=True)

        # Calculate cosine similarity scores
        cosine_scores = util.pytorch_cos_sim(search_embedding, comments_embeddings)[0]

        # Extract comments with similarity scores above the threshold
        related_issues = []
        for i, score in enumerate(cosine_scores):
            if score.item() >= self.threshold:
                issue = issues[i]
                issue.threshold = score.item()
                related_issues.append(issue)

        return related_issues
