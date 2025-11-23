"""
Base model for all SQLAlchemy ORM models.

This module defines the base class for all ORM models in the application.
It uses SQLAlchemy's declarative base feature and provides common columns
that can be inherited by other models, such as a primary key 'id'.
"""

from typing import Any

from sqlalchemy import Column, Integer
from sqlalchemy.orm import as_declarative, declared_attr


@as_declarative()
class Base:
    """
    Base class for all SQLAlchemy models.

    It provides a default __tablename__ generation and an 'id' primary key column.
    All ORM models in the application should inherit from this class.
    """
    id: Any
    __name__: str

    # Generate `__tablename__` automatically from the class name.
    # For example, a class `GameSession` will have a table name `gamesession`.
    @declared_attr
    def __tablename__(cls) -> str:
        """
        Generates the table name automatically based on the model's class name.
        """
        return cls.__name__.lower()

    # Define a common primary key column for all models.
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)