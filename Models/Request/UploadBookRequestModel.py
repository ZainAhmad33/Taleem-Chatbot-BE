from pydantic import BaseModel

class UploadBookRequestModel(BaseModel):
    filedata: str
    filename: str
