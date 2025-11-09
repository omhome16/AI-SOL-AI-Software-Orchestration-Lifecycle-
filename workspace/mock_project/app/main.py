# Mock FastAPI app

from fastapi import FastAPI
from .services.user_service import UserService

app = FastAPI()
user_service = UserService()

@app.get("/user/{name}")
def get_user(name: str):
    return user_service.get_user(name)
