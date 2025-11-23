import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

/**
 * Renders the main Tic-Tac-Toe game component.
 * It manages the game state, handles user interactions, and communicates
 * with the backend API to play the game.
 */
const Game = () => {
  // State for the game's unique identifier
  const [gameId, setGameId] = useState(null);
  // State for the 3x3 game board, represented as a 9-element array
  const [board, setBoard] = useState(Array(9).fill(null));
  // State for the current player ('X' or 'O')
  const [currentPlayer, setCurrentPlayer] = useState('X');
  // State to store the winner of the game
  const [winner, setWinner] = useState(null);
  // State to indicate if the game is a draw
  const [isDraw, setIsDraw] = useState(false);
  // State for handling and displaying API errors
  const [error, setError] = useState('');
  // State to manage loading indicators during API calls
  const [loading, setLoading] = useState(true);

  /**
   * Starts a new game by calling the backend API.
   * This function is memoized with useCallback to prevent unnecessary re-renders.
   */
  const startNewGame = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/games/');
      const { id, board, current_player, winner, is_draw } = response.data;
      setGameId(id);
      setBoard(board);
      setCurrentPlayer(current_player);
      setWinner(winner);
      setIsDraw(is_draw);
    } catch (err) {
      setError('Failed to start a new game. The server might be down.');
      console.error('Error starting new game:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // useEffect hook to automatically start a new game when the component mounts.
  useEffect(() => {
    startNewGame();
  }, [startNewGame]);

  /**
   * Handles a player's move when a cell is clicked.
   * @param {number} index - The index of the clicked cell (0-8).
   */
  const handleCellClick = async (index) => {
    // Prevent moves if the game is over, the cell is already taken, or a request is in progress.
    if (winner || isDraw || board[index] || loading) {
      return;
    }

    setLoading(true);
    setError('');
    try {
      // Send the move to the backend API
      const response = await api.post(`/games/${gameId}/move`, { position: index });
      const { board, current_player, winner, is_draw } = response.data;
      
      // Update the component's state with the new game state from the backend
      setBoard(board);
      setCurrentPlayer(current_player);
      setWinner(winner);
      setIsDraw(is_draw);
    } catch (err) {
      setError(err.response?.data?.detail || 'An invalid move was made or an error occurred.');
      console.error('Error making move:', err);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Determines the current status message of the game.
   * @returns {string} The status message to be displayed.
   */
  const getStatusMessage = () => {
    if (loading && !gameId) {
        return 'Connecting to server...';
    }
    if (winner) {
      return `Winner: ${winner}`;
    }
    if (isDraw) {
      return "It's a draw!";
    }
    return `Next Player: ${currentPlayer}`;
  };

  return (
    <>
      <style>{`
        .game-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
          margin-top: 40px;
          text-align: center;
        }

        .game-status {
          font-size: 24px;
          margin: 20px 0;
          font-weight: bold;
          min-height: 36px;
          color: #333;
        }

        .error-message {
          color: #d9534f;
          margin-bottom: 15px;
          min-height: 21px;
          font-weight: 500;
        }

        .game-board {
          display: grid;
          grid-template-columns: repeat(3, 100px);
          grid-template-rows: repeat(3, 100px);
          gap: 5px;
          border: 2px solid #333;
          background-color: #333;
          box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        .cell {
          width: 100px;
          height: 100px;
          background-color: #fff;
          border: none;
          font-size: 48px;
          font-weight: bold;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #333;
          transition: background-color 0.2s ease-in-out;
        }

        .cell:hover:not(:disabled) {
          background-color: #f0f0f0;
        }

        .cell:disabled {
          cursor: not-allowed;
        }

        .reset-button {
          margin-top: 25px;
          padding: 10px 20px;
          font-size: 18px;
          font-weight: bold;
          cursor: pointer;
          border: 2px solid #007bff;
          background-color: white;
          color: #007bff;
          border-radius: 5px;
          transition: background-color 0.3s, color 0.3s;
        }

        .reset-button:hover:not(:disabled) {
          background-color: #007bff;
          color: white;
        }

        .reset-button:disabled {
          border-color: #ccc;
          color: #ccc;
          cursor: not-allowed;
          background-color: #f9f9f9;
        }
      `}</style>
      <div className="game-container">
        <h1>Tic-Tac-Toe</h1>
        <div className="game-status">{getStatusMessage()}</div>
        {error && <div className="error-message">{error}</div>}
        <div className="game-board">
          {board.map((cellValue, index) => (
            <button
              key={index}
              className="cell"
              onClick={() => handleCellClick(index)}
              disabled={cellValue !== null || !!winner || isDraw || loading}
              aria-label={`Board cell ${index + 1}`}
            >
              {cellValue}
            </button>
          ))}
        </div>
        <button className="reset-button" onClick={startNewGame} disabled={loading}>
          {loading && gameId ? 'Processing...' : 'New Game'}
        </button>
      </div>
    </>
  );
};

export default Game;