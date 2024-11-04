from dataclasses import dataclass, field
from app.schemas.base_issue_schema import BaseIssueSchema
from app.models.issue_model import Issue

@dataclass
class IssueSchema(BaseIssueSchema):
    embedding: bytes = field(default_factory=bytes)
    shape: str = ""
    updated: str = ""

    def to_issue(self) -> Issue:
        return Issue(
            name=self.name,
            number=self.number,
            comments=self.comments,
            embedding=self.embedding,
            shape=self.shape,
            updated=self.updated
        )

    def __repr__(self):
        return f'<IssueSchema name={self.name} number={self.number}>'
