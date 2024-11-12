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
            self, name, number, comments=None, embedding=b'\x00\x01', shape='768', updated='2024-01-01'
        ):
        return Issue(
            name=name,
            number=number,
            comments=comments,
            embedding=embedding,
            shape=shape,
            updated=updated
        )

    def test_select_all_issues(self):
        insert_issues = [
            self.create_issue(name='Issue 1', number=1, shape='768', updated='2024-01-02'),
            self.create_issue(name='Issue 2', number=2, shape='768', updated='2024-01-03')
        ]
        IssueRepository.bulk_insert(insert_issues)

        issues = IssueRepository.select_all()
        assert len(issues) == 2

    def test_select_by_name(self):
        insert_issues = [
            self.create_issue(name='Unique Issue', number=3, shape='768', updated='2024-01-04'),
            self.create_issue(name='Issue 2', number=2, shape='768', updated='2024-01-03')
        ]
        IssueRepository.bulk_insert(insert_issues)

        issues = IssueRepository.select_by_name('Unique Issue')
        assert len(issues) == 1
        assert issues[0].number == 3
        assert issues[0].shape == '768'

    def test_bulk_insert(self):
        issues = [
            self.create_issue(name='Test Issue', number=1, comments=['Test comment1']),
            self.create_issue(name='Test Issue', number=2, comments=['Test comment2'])
        ]
        IssueRepository.bulk_insert(issues)
        retrieved_issue = Issue.query.all()
        assert len(retrieved_issue) == 2
        assert retrieved_issue[0].name == 'Test Issue'
        assert retrieved_issue[0].number == 1
        assert retrieved_issue[0].comments == ['Test comment1']
        assert retrieved_issue[0].embedding == b'\x00\x01'
        assert retrieved_issue[0].shape == '768'
        assert retrieved_issue[0].updated == '2024-01-01'
        assert retrieved_issue[1].name == 'Test Issue'
        assert retrieved_issue[1].number == 2
        assert retrieved_issue[1].comments == ['Test comment2']
        assert retrieved_issue[1].embedding == b'\x00\x01'
        assert retrieved_issue[1].shape == '768'
        assert retrieved_issue[1].updated == '2024-01-01'

    def test_delete_all_by_primary_key(self):
        insert_issues = [
            self.create_issue(name='Test Issue', number=1, comments=['Test comment1']),
            self.create_issue(name='Delete Issue', number=1, comments=['Test comment1']),
            self.create_issue(name='Delete Issue', number=2, comments=['Test comment2']),
        ]
        IssueRepository.bulk_insert(insert_issues)

        issues = [
            Issue(name='Delete Issue', number=1),
            Issue(name='Delete Issue', number=2),
        ]
        IssueRepository.delete_all_by_primary_key(issues)

        retrieved_issue = Issue.query.all()
        assert len(retrieved_issue) == 1
        assert retrieved_issue[0].name == 'Test Issue'
        assert retrieved_issue[0].number == 1
        assert retrieved_issue[0].comments == ['Test comment1']
