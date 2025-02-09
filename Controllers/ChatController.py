from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from Services.ChatService import ChatService, get_chat_service
from Models.Request.ChatRequestModel import ChatRequestModel

# for each controller 
# prefix specifies actions route
# tags specifies actions group name for documentation (swagger)

router = APIRouter(
    prefix="/items",
    tags=["items"],
)

# injecting service dependency
chat_service_dependency = Annotated[ChatService, Depends(get_chat_service)]

@router.get("")
async def read_items(chat_service: chat_service_dependency):
    res = chat_service.chat_history
    return {"res": res}

@router.post("/uploadBook")
async def upload_book(chat_service: chat_service_dependency):
    res = chat_service.add_document('./Content/Physics9.pdf')
    return {"res": res}

@router.post("/askQuestion")
async def upload_book(chat_data: ChatRequestModel, chat_service: chat_service_dependency):
    res = await chat_service.ask_question(chat_data)
    return {"res": res}
