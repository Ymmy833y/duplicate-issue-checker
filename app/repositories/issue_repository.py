import logging
from typing import List
from app import db
from app.models.issue_model import Issue

logger = logging.getLogger(__name__)

class IssueRepository:
    @staticmethod
    def select_all() -> List[Issue]:
        return Issue.query.all()

    @staticmethod
    def select_by_name(name: str) -> List[Issue]:
        logger.info('Selecting issues by name: %s', name)
        issues = Issue.query.filter(Issue.name == name).all()
        logger.info('Selected %d issues for name: %s', len(issues), name)
        return issues

    @staticmethod
    def bulk_insert(issues: List[Issue]):
        logger.info('Inserting %d issues in bulk', len(issues))
        db.session.bulk_save_objects(issues)
        db.session.commit()
        logger.info('Bulk insert completed')

    @staticmethod
    def delete_all_by_primary_key(issues: List[Issue]):
        issue_names = [issue.name for issue in issues]
        issue_numbers = [issue.number for issue in issues]
        logger.info('Deleting %d issues by primary key: %s', len(issues), list(zip(issue_names, issue_numbers)))

        Issue.query.filter(
            Issue.name.in_(issue_names), Issue.number.in_(issue_numbers)
        ).delete(synchronize_session=False)
        db.session.commit()
        logger.info('Deletion by primary key completed')
