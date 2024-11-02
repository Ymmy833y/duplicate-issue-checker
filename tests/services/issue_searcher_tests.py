from unittest.mock import patch, MagicMock

from app.services.issue_searcher import preprocess_text, IssueSearcher
from app.schemas.issue_schema import Issue

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
    @patch('app.services.issue_searcher.util.pytorch_cos_sim')
    @patch('app.services.issue_searcher.SentenceTransformer.encode')
    def test_success(self, mock_encode, mock_pytorch_cos_sim):
        issues = [
            Issue(
                number=1, title="Issue 1", url="http://example.com/1",
                state="open", comments=["This is a test comment."]
            ),
            Issue(
                number=2, title="Issue 2", url="http://example.com/2",
                state="open", comments=["Another test comment."]
            )
        ]
        title = "Test"
        description = "This is a test description."

        mock_encode.side_effect = lambda x, convert_to_tensor: MagicMock()

        score1 = MagicMock()
        score1.item.return_value = 0.9
        score2 = MagicMock()
        score2.item.return_value = 0.3
        cosine_scores_list = [score1, score2]

        mock_cosine_scores = MagicMock()
        mock_cosine_scores.__getitem__.return_value = cosine_scores_list
        mock_pytorch_cos_sim.return_value = mock_cosine_scores

        searcher = IssueSearcher()
        searcher.set_threshold(0.5)

        related_issues = searcher.find_related_issues(issues, title, description)

        assert len(related_issues) == 1
        assert related_issues[0].number == 1
        mock_encode.assert_any_call(preprocess_text(f"{title}: {description}"), convert_to_tensor=True)
        mock_encode.assert_any_call([
            preprocess_text(f"{issue.title}: {' '.join(issue.comments)}") for issue in issues
        ], convert_to_tensor=True)
        mock_pytorch_cos_sim.assert_called_once()
