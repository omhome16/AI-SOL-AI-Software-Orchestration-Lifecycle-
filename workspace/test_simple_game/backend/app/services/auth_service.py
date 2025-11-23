"""
Service layer for authentication-related operations.

This module contains the business logic for handling users, such as
retrieving, creating, and authenticating them. It acts as an intermediary
between the API endpoints and the database models.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate
from app.security import get_password_hash, verify_password


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """
    Retrieves a user from the database by their username.

    Args:
        db (Session): The database session.
        username (str): The username to search for.

    Returns:
        Optional[User]: The User object if found, otherwise None.
    """
    return db.query(User).filter(User.username == username).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Authenticates a user by checking their username and password.

    First, it retrieves the user by username. If the user exists, it then
    verifies the provided password against the stored hashed password.

    Args:
        db (Session): The database session.
        username (str): The user's username.
        password (str): The user's plain-text password.

    Returns:
        Optional[User]: The authenticated User object if credentials are valid,
                        otherwise None.
    """
    user = get_user_by_username(db, username=username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_user(db: Session, user_in: UserCreate) -> User:
    """
    Creates a new user in the database.

    This function takes user creation data, hashes the password, and creates
    a new User record in the database.

    Args:
        db (Session): The database session.
        user_in (UserCreate): The Pydantic schema containing the new user's data,
                              including a plain-text password.

    Returns:
        User: The newly created User object, with data loaded from the database.
    """
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user