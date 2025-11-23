"""
FastAPI router for user-related endpoints.

This module provides API endpoints for user registration and authentication (token generation).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import User, UserCreate
from app.schemas.token import Token
from app.services import auth_service
from app.security import create_access_token

router = APIRouter()


@router.post(
    "/",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    tags=["Users"],
)
def create_new_user(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    """
    Create a new user in the system.

    - **email**: User's email address (must be unique).
    - **username**: User's username (must be unique).
    - **password**: User's password.

    Raises an HTTPException with status code 400 if a user with the same
    username already exists.
    """
    existing_user = auth_service.get_user_by_username(db, username=user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this username already exists.",
        )

    user = auth_service.create_user(db=db, user_in=user_in)
    return user


@router.post(
    "/token",
    response_model=Token,
    summary="Get an access token",
    tags=["Authentication"],
)
def login_for_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Token:
    """
    OAuth2-compliant endpoint to get an access token for a user.

    Authenticates a user based on username and password provided in the form data
    and returns a JWT access token.

    - **username**: The user's username.
    - **password**: The user's password.

    Raises an HTTPException with status code 401 if authentication fails.
    """
    user = auth_service.authenticate_user(
        db, username=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=user.username)

    return Token(access_token=access_token, token_type="bearer")