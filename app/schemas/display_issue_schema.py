from dataclasses import dataclass
from app.schemas.base_issue_schema import BaseIssueSchema
from app.schemas.issue_schema import IssueSchema

@dataclass
class DisplayIssueSchema(BaseIssueSchema):
    @classmethod
    def from_issue_schema(cls, issue_schema: IssueSchema) -> 'DisplayIssueSchema':
        return cls(
            name=issue_schema.name,
            number=issue_schema.number,
            title=issue_schema.title,
            url=issue_schema.url,
            state=issue_schema.state,
            comments=issue_schema.comments,
            threshold=issue_schema.threshold
        )

    def __repr__(self):
        return f'<DisplayIssueSchema name={self.name} number={self.number} title={self.title}>'
