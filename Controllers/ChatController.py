from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from Services.ChatService import ChatService, get_chat_service

# for each controller 
# prefix specifies actions route
# tags specifies actions group name for documentation (swagger)

router = APIRouter(
    prefix="/items",
    tags=["items"],
)

fake_items_db = {"plumbus": {"name": "Plumbus"}, "gun": {"name": "Portal Gun"}}
# injecting service dependency
chat_service_dependency = Annotated[ChatService, Depends(get_chat_service)]

@router.get("/")
async def read_items(chat_service: chat_service_dependency):
    res = chat_service.chat_history
    return {"res": res}
