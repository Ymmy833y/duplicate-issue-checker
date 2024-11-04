from dataclasses import dataclass
from typing import List, Optional

@dataclass
class BaseIssueSchema:
    name: str
    number: int
    title: str
    url: str
    state: str
    comments: List[str]
    threshold: Optional[float] = None
