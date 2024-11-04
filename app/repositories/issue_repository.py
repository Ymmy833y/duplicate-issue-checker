from typing import List
from app import db
from app.models.issue_model import Issue

class IssueRepository:
    @staticmethod
    def select_all() -> List[Issue]:
        return Issue.query.all()

    @staticmethod
    def select_by_name(name: str) -> List[Issue]:
        return Issue.query.filter(Issue.name == name).all()

    @staticmethod
    def insert(issue: Issue):
        db.session.add(issue)
        db.session.commit()

    @staticmethod
    def update(new_issue: Issue):
        issue = Issue.query.filter_by(name=new_issue.name, number=new_issue.number).first()

        if issue is None:
            return False

        if new_issue.comments is not None:
            issue.comments = new_issue.comments
        if new_issue.embedding is not None:
            issue.embedding = new_issue.embedding
        if new_issue.shape is not None:
            issue.shape = new_issue.shape
        if new_issue.updated is not None:
            issue.updated = new_issue.updated

        db.session.commit()
        return True
