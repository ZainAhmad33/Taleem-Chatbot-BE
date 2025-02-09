from pydantic import BaseModel
from typing import List

from Models.Request.MessageRequestModel import MessageRequestModel

class ChatRequestModel(BaseModel):
    grade: str
    course: str
    historical_question: str
    chat: List[MessageRequestModel]
    
