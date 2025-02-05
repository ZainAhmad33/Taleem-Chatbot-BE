from fastapi import APIRouter, Depends, HTTPException

# for each controller 
# prefix specifies actions route
# tags specifies actions group name for documentation (swagger)

router = APIRouter(
    prefix="/items",
    tags=["items"],
)

fake_items_db = {"plumbus": {"name": "Plumbus"}, "gun": {"name": "Portal Gun"}}

@router.get("/")
async def read_items():
    return fake_items_db
