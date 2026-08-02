from pydantic import BaseModel
from typing import List


class GreetingResponse(BaseModel):
    text: str
    chips: List[str]
    scenario: str  # for debugging/QA — which template was chosen
