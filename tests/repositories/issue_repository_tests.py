# pylint: disable=W0621

import pytest
from app import create_app, db
from app.models.issue_model import Issue
from app.repositories.issue_repository import IssueRepository

from tests.testing_config import TestingConfig

@pytest.fixture(scope='function')
def test_app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

class TestIssueRepository:
    @pytest.fixture(autouse=True)
    def setup_method(self, test_app):
        with test_app.app_context():
            db.session.query(Issue).delete()
            db.session.commit()

    def create_issue(
            self, name, number, comments=None, embedding=b'\x00\x01', shape='circle', updated='2024-01-01'
        ):
        return Issue(
            name=name,
            number=number,
            comments=comments,
            embedding=embedding,
            shape=shape,
            updated=updated
        )

    def test_insert_issue(self):
        issue = self.create_issue(name='Test Issue', number=1, comments=['Test comment'])
        IssueRepository.insert(issue)
        retrieved_issue = Issue.query.first()
        assert retrieved_issue.name == 'Test Issue'
        assert retrieved_issue.number == 1
        assert retrieved_issue.comments == ['Test comment']
        assert retrieved_issue.embedding == b'\x00\x01'
        assert retrieved_issue.shape == 'circle'
        assert retrieved_issue.updated == '2024-01-01'

    def test_select_all_issues(self):
        issue1 = self.create_issue(name='Issue 1', number=1, shape='square', updated='2024-01-02')
        issue2 = self.create_issue(name='Issue 2', number=2, shape='triangle', updated='2024-01-03')
        IssueRepository.insert(issue1)
        IssueRepository.insert(issue2)
        issues = IssueRepository.select_all()
        assert len(issues) == 2

    def test_select_by_name(self):
        issue = self.create_issue(name='Unique Issue', number=3, shape='hexagon', updated='2024-01-04')
        IssueRepository.insert(issue)
        issues = IssueRepository.select_by_name('Unique Issue')
        assert len(issues) == 1
        assert issues[0].number == 3
        assert issues[0].shape == 'hexagon'

    def test_update_issue(self):
        issue = self.create_issue(
            name='Update Issue', number=4, comments=['Old comment'], shape='pentagon', updated='2024-01-05'
        )
        IssueRepository.insert(issue)

        updated_issue = self.create_issue(
            name='Update Issue', number=4, comments=['New comment'],
            embedding=b'\x00\x05', shape='octagon', updated='2024-01-06'
        )
        success = IssueRepository.update(updated_issue)
        assert success is True

        retrieved_issue = Issue.query.filter_by(name='Update Issue', number=4).first()
        assert retrieved_issue.comments == ['New comment']
        assert retrieved_issue.embedding == b'\x00\x05'
        assert retrieved_issue.shape == 'octagon'
        assert retrieved_issue.updated == '2024-01-06'

    def test_update_nonexistent_issue(self):
        updated_issue = self.create_issue(name='Nonexistent Issue', number=5, shape='circle', updated='2024-01-07')
        success = IssueRepository.update(updated_issue)
        assert success is False
