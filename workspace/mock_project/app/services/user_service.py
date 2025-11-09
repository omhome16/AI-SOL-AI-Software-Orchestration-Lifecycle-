# Mock User service

from ..models.user import User

class UserService:
    def get_user(self, name: str) -> User:
        return User(name)
