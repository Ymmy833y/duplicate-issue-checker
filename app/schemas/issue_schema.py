from dataclasses import dataclass
from typing import List, Optional

@dataclass
class Issue:
    number: int
    title: str
    url: str
    state: str
    comments: List[str]
    threshold: Optional[float] = None
