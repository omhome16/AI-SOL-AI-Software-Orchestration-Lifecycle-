"""
Pydantic schemas for User models.

This module defines the Pydantic models for data validation and serialization
for user-related API endpoints. These schemas are used by FastAPI to validate
incoming request data and to format outgoing response data.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    """
    Base schema for user properties.
    Shared attributes for all user-related schemas.
    """
    email: EmailStr
    username: str


class UserCreate(UserBase):
    """
    Schema for user creation.
    Used as the request body when creating a new user.
    Includes the password which is required for creation.
    """
    password: str


class UserLogin(BaseModel):
    """
    Schema for user login.
    Used as the request body for the authentication endpoint.
    """
    username: str
    password: str


class User(UserBase):
    """
    Schema for representing a user in API responses.
    This model is used when returning user data from the API.
    It inherits from UserBase and adds fields that are safe to expose.
    It does NOT include the password.
    """
    id: int
    is_active: bool

    class Config:
        """
        Pydantic configuration.
        'from_attributes = True' allows the model to be created from ORM objects.
        """
        from_attributes = True


class Token(BaseModel):
    """
    Schema for the JWT access token response.
    This is the response model for a successful login.
    """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Schema for the data encoded within a JWT.
    This is used to validate the token's payload and identify the user.
    """
    username: Optional[str] = None