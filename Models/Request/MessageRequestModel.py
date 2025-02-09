from pydantic import BaseModel

class MessageRequestModel(BaseModel):
    content: str
    role: str
