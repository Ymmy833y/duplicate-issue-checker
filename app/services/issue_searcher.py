import re
from typing import List

import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util

from app.schemas.issue_schema import IssueSchema
from app.schemas.display_issue_schema import DisplayIssueSchema

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

    def generate_serialized_embedding(self, title: str, comments: List[str]) -> tuple[bytes, str]:
        """
        Generate a serialized embedding for a given title and associated comments.

        :param title: The title for which the embedding is generated.
        :param comments: A list of comment strings associated with the title.

        :return: A tuple containing:
        - A bytes object of the embedding in serialized format.
        - A string representing the shape of the embedding in the format 'dim1,dim2,...'.
        """
        comment = '' if comments is None else ' '.join(
            comment if comment is not None else '' for comment in comments
        )
        embeddings = self.model.encode(preprocess_text(f'{title}: {comment}'), convert_to_tensor=False)
        embedding_np = embeddings.astype(np.float32)
        return embedding_np.tobytes(), ','.join(map(str, embedding_np.shape))

    def deserialize_embedding(self, byte_data: bytes, shape_str: str) -> torch.Tensor:
        """
        Deserialize a serialized embedding into a tensor.

        :param byte_data: The byte array containing the serialized embedding.
        :param shape_str: A string representing the shape of the embedding in the format 'dim1,dim2,...'.

        :return: A torch.Tensor reconstructed from the byte data with the specified shape.
        """
        shape = tuple(map(int, shape_str.split(',')))
        np_array = np.frombuffer(byte_data, dtype=np.float32).reshape(shape)
        return torch.from_numpy(np_array.copy())

    def find_related_issues(self, issues: List[IssueSchema], title: str, description: str) -> List[DisplayIssueSchema]:
        """
        Find issue comments that are semantically similar to the search query using SBERT.

        :param issues: List of issue to search within
        :param title: Search query
        :param description: Search query
        :return: A list of issues that exceed a threshold
        """
        # Deserializing issue comments
        comments_embeddings = torch.stack([
            self.deserialize_embedding(issue.embedding, issue.shape) for issue in issues
        ])

        # Encode the search query
        search_embedding = self.model.encode(preprocess_text(f'{title}: {description}'), convert_to_tensor=True)

        # Calculate cosine similarity scores
        cosine_scores = util.pytorch_cos_sim(search_embedding, comments_embeddings)[0]

        # Extract comments with similarity scores above the threshold
        related_issues = []
        for i, score in enumerate(cosine_scores):
            if score.item() >= self.threshold:
                issue = issues[i]
                issue.threshold = score.item()
                related_issues.append(DisplayIssueSchema.from_issue_schema(issue))
        return related_issues
