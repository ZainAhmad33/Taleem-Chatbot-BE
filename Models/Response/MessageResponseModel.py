from pydantic import BaseModel
from typing import List, Optional

import Helpers

class MessageResponseModel(BaseModel):
    role: str
    content: List[str]
    feedback: int = 2
    references: List[str]
    pages: Optional[List[int]]
    is_loading: bool = False
    historical_question: str
    reasoning: str
    
    @classmethod
    def create(cls, _role: str, _content: str, _pages: set, _references: List[str], _historical_question:str, _reasoning: str):
        return cls(
            role = _role,
            content = Helpers.remove_newlines_in_latex(_content).split('\n'),
            references = [Helpers.extract_two_sentences(Helpers.remove_newlines(text)) for text in _references],
            pages =  [i + 1 for i in _pages],
            historical_question = _historical_question,
            reasoning = _reasoning
        )