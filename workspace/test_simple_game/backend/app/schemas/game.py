from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime

# --- Move Schemas ---

class MoveCreate(BaseModel):
    """
    Schema for a player making a move.
    Represents the data sent by a client when a player takes a turn.
    """
    position: int = Field(
        ...,
        ge=0,
        le=8,
        description="The position on the board to place a mark (0-8, left-to-right, top-to-bottom)."
    )


# --- Game Schemas ---

class GameBase(BaseModel):
    """
    Base schema for a game, containing the core game state.
    """
    board: List[str] = Field(
        default_factory=lambda: [""] * 9,
        description="The 3x3 game board represented as a list of 9 strings ('X', 'O', or '')."
    )
    current_player: str = Field(
        default='X',
        description="The player whose turn it is ('X' or 'O')."
    )
    status: str = Field(
        default='in_progress',
        description="The current status of the game (e.g., 'in_progress', 'finished')."
    )
    winner: Optional[str] = Field(
        default=None,
        description="The winner of the game ('X', 'O') or None if no winner yet or it's a draw."
    )

    @validator('board')
    def board_must_have_9_elements(cls, v: List[str]) -> List[str]:
        """Validates that the board has exactly 9 cells."""
        if len(v) != 9:
            raise ValueError('Board must contain exactly 9 elements.')
        for cell in v:
            if cell not in ('X', 'O', ''):
                raise ValueError("Board cells can only be 'X', 'O', or ''.")
        return v

    @validator('current_player')
    def player_must_be_x_or_o(cls, v: str) -> str:
        """Validates that the current player is either 'X' or 'O'."""
        if v not in ('X', 'O'):
            raise ValueError("Current player must be 'X' or 'O'.")
        return v

    @validator('status')
    def status_is_valid(cls, v: str) -> str:
        """Validates the game status."""
        valid_statuses = ['in_progress', 'finished']
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}.")
        return v

    @validator('winner')
    def winner_must_be_x_or_o_or_none(cls, v: Optional[str]) -> Optional[str]:
        """Validates the winner value."""
        if v is not None and v not in ('X', 'O'):
            raise ValueError("Winner must be 'X', 'O', or None.")
        return v


class GameCreate(BaseModel):
    """
    Schema for creating a new game.
    This is intentionally empty as new games start with a default state.
    The owner is determined from the authenticated user making the request.
    """
    pass


class Game(GameBase):
    """
    Schema for representing a game instance, including database-generated fields.
    Used for API responses to clients.
    """
    id: int = Field(..., description="The unique identifier for the game.")
    owner_id: int = Field(..., description="The ID of the user who created the game.")
    created_at: datetime = Field(..., description="The timestamp when the game was created.")
    updated_at: datetime = Field(..., description="The timestamp when the game was last updated.")

    class Config:
        """Pydantic configuration."""
        orm_mode = True