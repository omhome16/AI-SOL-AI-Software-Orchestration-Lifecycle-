"""
FastAPI router for game-related endpoints.

This module defines the API routes for managing the game state, including
starting a new game, retrieving the current state, and making a move.
All endpoints in this router require user authentication.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.game import Game, MoveCreate
from app.models.user import User
from app.services import game_service, auth_service
from app.database.session import get_db

router = APIRouter(
    prefix="/game",
    tags=["Game"],
    responses={404: {"description": "Not found"}},
)


@router.post("/start", response_model=Game)
def start_new_game(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_active_user),
):
    """
    Starts a new game for the authenticated user.

    This endpoint resets the game board and state, allowing the user to
    begin a fresh match. If no game state exists for the user, it will be
    created and then set to the default starting state.

    Args:
        db (Session): The database session, injected by FastAPI.
        current_user (User): The authenticated user, injected by FastAPI.

    Returns:
        Game: The initial state of the new game.
    """
    # The game service handles the logic of finding or creating the game state
    # and resetting it to the initial values for a new game.
    game_state = game_service.start_new_game(db=db, user_id=current_user.id)
    return game_state


@router.get("/state", response_model=Game)
def get_game_state(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_active_user),
):
    """
    Retrieves the current game state for the authenticated user.

    If a game is in progress, it returns the current board, turn, and status.
    If no game has been started for the user, it initializes and returns a
    new game state with default values.

    Args:
        db (Session): The database session, injected by FastAPI.
        current_user (User): The authenticated user, injected by FastAPI.

    Returns:
        Game: The user's current game state.
    """
    game_state = game_service.get_game_state_for_user(db=db, user_id=current_user.id)
    return game_state


@router.post("/move", response_model=Game)
def make_move(
    move: MoveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_service.get_current_active_user),
):
    """
    Processes a player's move in the current game.

    The user submits a position on the board (0-8). The server validates
    the move, updates the board, checks for a win or draw condition, and
    returns the new game state.

    Args:
        move (MoveCreate): The move data from the request body,
                           containing the board position.
        db (Session): The database session, injected by FastAPI.
        current_user (User): The authenticated user making the move.

    Returns:
        Game: The updated game state after the move.

    Raises:
        HTTPException: A 400 Bad Request if the move is invalid (e.g.,
                       position taken, game is over, not player's turn).
    """
    # The game_service.process_player_move function is expected to handle
    # all game logic and validation, raising HTTPException on errors.
    updated_game_state = game_service.process_player_move(
        db=db, user_id=current_user.id, position=move.position
    )
    return updated_game_state