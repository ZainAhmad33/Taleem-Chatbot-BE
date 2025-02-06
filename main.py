from fastapi import FastAPI
from Controllers import ChatController

app = FastAPI()

# Register controllers here
app.include_router(ChatController.router)
