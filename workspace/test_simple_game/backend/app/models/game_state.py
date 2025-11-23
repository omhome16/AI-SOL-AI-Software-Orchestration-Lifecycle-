"""
SQLAlchemy ORM model for a GameState.

This module defines the GameState model, which corresponds to the 'game_states'
table in the database. It stores user-specific game progress, such as their
current score and level. Each game state is linked to a specific user.
"""

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import backref, relationship

from .base import Base


class GameState(Base):
    """
    Represents the game progress for a single user.

    This model maps to the 'game_states' table and holds data like score and
    level. It has a one-to-one relationship with the User model.

    Attributes:
        id (int): The primary key for the game state, inherited from Base.
        score (int): The user's current score in the game. Defaults to 0.
        level (int): The user's current level in the game. Defaults to 1.
        user_id (int): A foreign key linking to the 'users' table.
        user (User): The SQLAlchemy relationship to the associated User object.
    """
    __tablename__ = "game_states"

    score = Column(Integer, nullable=False, default=0)
    level = Column(Integer, nullable=False, default=1)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Establishes a one-to-one relationship with the User model.
    # The `backref` creates a `game_state` attribute on the User model,
    # and `uselist=False` ensures it's a scalar attribute (one-to-one).
    user = relationship("User", backref=backref("game_state", uselist=False))

    def __repr__(self) -> str:
        """
        Provides a developer-friendly string representation of the GameState object.
        """
        return (
            f"<GameState(id={self.id}, user_id={self.user_id}, "
            f"score={self.score}, level={self.level})>"
        )