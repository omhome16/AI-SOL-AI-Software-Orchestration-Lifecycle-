from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.game_state import GameState
from app.models.user import User


def get_game_state_for_user(db: Session, user_id: int) -> GameState:
    """
    Retrieves the game state for a specific user.

    If no game state exists for the user, a new one is created with default
    values (score=0, level=1).

    Args:
        db (Session): The database session.
        user_id (int): The ID of the user.

    Returns:
        GameState: The user's game state object.
    
    Raises:
        HTTPException: If the user with the given user_id does not exist.
    """
    game_state = db.query(GameState).filter(GameState.user_id == user_id).first()

    if not game_state:
        # Check if user exists before creating a game state for them
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found",
            )
        
        new_game_state = GameState(user_id=user_id, score=0, level=1)
        db.add(new_game_state)
        db.commit()
        db.refresh(new_game_state)
        return new_game_state

    return game_state


def update_user_score(db: Session, user_id: int, points_to_add: int = 1) -> GameState:
    """
    Updates the score for a given user by adding a specified number of points.

    Args:
        db (Session): The database session.
        user_id (int): The ID of the user whose score to update.
        points_to_add (int): The number of points to add to the score. Defaults to 1.

    Returns:
        GameState: The updated game state object.
    """
    game_state = get_game_state_for_user(db, user_id)
    game_state.score += points_to_add
    db.add(game_state)
    db.commit()
    db.refresh(game_state)
    return game_state


def _check_winner(board: List[List[Optional[str]]]) -> Optional[str]:
    """
    Checks for a winner in a 3x3 Tic-Tac-Toe game.

    Args:
        board (List[List[Optional[str]]]): The 3x3 game board.

    Returns:
        Optional[str]: The winning player ('X' or 'O'), or None if there is no winner.
    """
    # Check rows
    for row in board:
        if row[0] is not None and row[0] == row[1] == row[2]:
            return row[0]

    # Check columns
    for col in range(3):
        if board[0][col] is not None and board[0][col] == board[1][col] == board[2][col]:
            return board[0][col]

    # Check diagonals
    if board[0][0] is not None and board[0][0] == board[1][1] == board[2][2]:
        return board[0][0]
    if board[0][2] is not None and board[0][2] == board[1][1] == board[2][0]:
        return board[0][2]

    return None


def _is_board_full(board: List[List[Optional[str]]]) -> bool:
    """
    Checks if the Tic-Tac-Toe board is full.

    Args:
        board (List[List[Optional[str]]]): The 3x3 game board.

    Returns:
        bool: True if the board is full, False otherwise.
    """
    for row in board:
        for cell in row:
            if cell is None:
                return False
    return True


def process_player_move(
    db: Session,
    user_id: int,
    board: List[List[Optional[str]]],
    row: int,
    col: int,
    player: str,
) -> Dict[str, Any]:
    """
    Processes a player's move in a Tic-Tac-Toe game.

    This function validates the move, updates the board state, checks for a
    win or draw condition, and updates the player's score if they win.

    Args:
        db (Session): The database session.
        user_id (int): The ID of the user making the move.
        board (List[List[Optional[str]]]): The current 3x3 game board.
        row (int): The row of the move (0-2).
        col (int): The column of the move (0-2).
        player (str): The player making the move ('X' or 'O').

    Raises:
        HTTPException: If the move is invalid (out of bounds, cell already taken,
                       or invalid player).

    Returns:
        Dict[str, Any]: A dictionary containing the updated game state, including
                        the new board, game status ('ongoing', 'win', 'draw'),
                        the winner (if any), and the next player's turn.
    """
    # --- Input Validation ---
    if not (0 <= row < 3 and 0 <= col < 3):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Move is out of bounds. Row and column must be between 0 and 2.",
        )

    if player not in ["X", "O"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid player. Must be 'X' or 'O'.",
        )

    if board[row][col] is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cell is already taken.",
        )

    # --- Apply Move ---
    board[row][col] = player

    # --- Check Game Status ---
    winner = _check_winner(board)
    if winner:
        # If the user making the move is the winner, update their score
        if winner == player:
            update_user_score(db, user_id, points_to_add=1)
        
        return {
            "board": board,
            "status": "win",
            "winner": winner,
            "next_player": None,
        }

    if _is_board_full(board):
        return {
            "board": board,
            "status": "draw",
            "winner": None,
            "next_player": None,
        }

    # --- Game Continues ---
    next_player = "O" if player == "X" else "X"
    return {
        "board": board,
        "status": "ongoing",
        "winner": None,
        "next_player": next_player,
    }