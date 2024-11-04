from unittest.mock import patch

import numpy as np
import torch

from app.services.issue_searcher import preprocess_text, IssueSearcher
from app.schemas.issue_schema import IssueSchema

class TestPreprocessText:
    def test_not_text(self):
        input_text = None
        expected_output = ''
        assert preprocess_text(input_text) == expected_output

    def test_remove_urls(self):
        input_text = 'Check out this link: http://example.com and https://another.com/page'
        expected_output = 'check out this link and'
        assert preprocess_text(input_text) == expected_output

    def test_remove_mentions(self):
        input_text = 'Hello @user1 and @user2, welcome!'
        expected_output = 'hello and welcome'
        assert preprocess_text(input_text) == expected_output

    def test_remove_hashtags(self):
        input_text = 'This is a #test of the #preprocess_text function.'
        expected_output = 'this is a of the function'
        assert preprocess_text(input_text) == expected_output

    def test_remove_special_characters(self):
        input_text = 'Hello, World! This is a test. #100DaysOfCode @python_dev'
        expected_output = 'hello world this is a test'
        assert preprocess_text(input_text) == expected_output

    def test_multiple_spaces(self):
        input_text = 'This    is  a     test.'
        expected_output = 'this is a test'
        assert preprocess_text(input_text) == expected_output

    def test_already_clean_text(self):
        input_text = 'This text is already clean and has no special elements'
        expected_output = 'this text is already clean and has no special elements'
        assert preprocess_text(input_text) == expected_output

class TestIssueSearcher:
    @patch('app.services.issue_searcher.SentenceTransformer.encode')
    def test_generate_serialized_embedding(self, mock_encode):
        searcher = IssueSearcher()

        title = 'Issue Title'
        comments = ['Comment one.', 'Comment two.']
        input_text = preprocess_text(f"{title}: {' '.join(comments)}")

        embedding_np = np.random.rand(768).astype(np.float32)
        mock_encode.return_value = embedding_np

        embedding_bytes, shape_str = searcher.generate_serialized_embedding(title, comments)

        mock_encode.assert_called_once_with(input_text, convert_to_tensor=False)

        assert embedding_bytes == embedding_np.tobytes()
        assert shape_str == '768'

    def test_deserialize_embedding(self):
        searcher = IssueSearcher()

        embedding_np = np.random.rand(768).astype(np.float32)
        embedding_bytes = embedding_np.tobytes()
        shape_str = '768'

        deserialized_embedding = searcher.deserialize_embedding(embedding_bytes, shape_str)

        assert torch.allclose(torch.from_numpy(embedding_np), deserialized_embedding)

    def test_find_related_issues(self):
        searcher = IssueSearcher()
        searcher.set_threshold(0.5)

        # Manually set the embedding vector
        # fake_embedding_2 and fake_search_embedding are set to the same vector to increase the similarity
        fixed_vector = np.ones(768, dtype=np.float32)
        fake_embedding_2 = fixed_vector
        fake_search_embedding = fixed_vector

        # fake_embedding_1 is set to a different vector (low similarity)
        fake_embedding_1 = np.zeros(768, dtype=np.float32)

        # Serialize embedding
        issue_embedding_1 = fake_embedding_1.tobytes()
        issue_shape_1 = '768'
        issue_embedding_2 = fake_embedding_2.tobytes()
        issue_shape_2 = '768'

        # Mock SentenceTransformer.encode
        with patch.object(searcher.model, 'encode', return_value=fake_search_embedding):
            issues = [
                IssueSchema(
                    name='test_owner/test_repo',
                    number=1,
                    title='issue 1',
                    url='https://github.com/test_owner/test_repo/issues/1',
                    state='close',
                    comments=['Comment1'],
                    embedding=issue_embedding_1,
                    shape=issue_shape_1,
                    updated='2024-01-01'
                ),
                IssueSchema(
                    name='test_owner/test_repo',
                    number=2,
                    title='issue 2',
                    url='https://github.com/test_owner/test_repo/issues/2',
                    state='open',
                    comments=['Comment 2'],
                    embedding=issue_embedding_2,
                    shape=issue_shape_2,
                    updated='2024-01-01'
                )
            ]
            title = 'title'
            description = 'description'

            related_issues = searcher.find_related_issues(issues, title, description)

        assert len(related_issues) == 1
        assert related_issues[0].number == 2
