"""
Security-related utilities for password hashing and JWT token management.

This module provides functions for:
- Hashing and verifying passwords using passlib with the bcrypt algorithm.
- Creating and decoding JWT access tokens using python-jose.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings
from app.schemas.token import TokenData

# Setup for password hashing using bcrypt algorithm
# This context will be used to hash new passwords and verify existing ones.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Algorithm for JWT encoding and decoding
ALGORITHM = "HS256"


def create_access_token(subject: Any, expires_delta: timedelta | None = None) -> str:
    """
    Generates a JWT access token.

    The token contains a subject ('sub') claim and an expiration ('exp') claim.

    Args:
        subject: The subject of the token, typically a user ID or username.
                 It will be converted to a string.
        expires_delta: The lifespan of the token from the current time. If None,
                       it defaults to the value of ACCESS_TOKEN_EXPIRE_MINUTES
                       from the application settings.

    Returns:
        The encoded JWT access token as a string.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a hashed password.

    Args:
        plain_password: The password in plain text to verify.
        hashed_password: The stored hashed password to compare against.

    Returns:
        True if the passwords match, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hashes a plain-text password using the configured algorithm (bcrypt).

    Args:
        password: The plain-text password to hash.

    Returns:
        The resulting hashed password as a string.
    """
    return pwd_context.hash(password)


def decode_token(token: str) -> TokenData | None:
    """
    Decodes a JWT token and validates its payload into a TokenData schema.

    This function verifies the token's signature and expiration. If the token
    is valid and contains a subject ('sub') claim, it returns the payload
    as a TokenData object.

    Args:
        token: The JWT token string to decode.

    Returns:
        A TokenData object containing the username if the token is valid,
        otherwise None.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            return None
        return TokenData(username=username)
    except JWTError:
        # This catches any error from jose, including expired signature,
        # invalid signature, etc.
        return None