"""
SQLAlchemy ORM model for a User.

This module defines the User model, which corresponds to the 'users' table
in the database. It stores user authentication information, including a unique
username and a hashed password.
"""

from sqlalchemy import Column, String

from .base import Base


class User(Base):
    """
    Represents a user in the system.

    This model maps to the 'users' table and contains the essential
    credentials for a user to authenticate with the application.

    Attributes:
        id (int): The primary key for the user, inherited from Base.
        username (str): The user's unique username, used for logging in.
        hashed_password (str): The user's password, hashed for security.
    """
    __tablename__ = "users"

    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    def __repr__(self) -> str:
        """
        Provides a developer-friendly string representation of the User object.
        """
        return f"<User(id={self.id}, username='{self.username}')>"