"""
Pydantic schemas for JWT token data and responses.
"""
from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    """
    Represents the structure of the access token response sent to the client
    upon successful authentication.
    """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Represents the data payload encoded within a JWT.
    This schema is used to validate the token's contents after decoding.
    """
    username: Optional[str] = None