from typing import Union

from fastapi import FastAPI
from Controllers import DummyController

app = FastAPI()

# Register controllers here
app.include_router(DummyController.router)
