from dataclasses import dataclass

@dataclass
class IssueDetaiSchema:
    total: int
    message: str
