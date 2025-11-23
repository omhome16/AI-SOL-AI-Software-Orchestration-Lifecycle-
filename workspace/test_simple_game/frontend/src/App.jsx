import React, { useState, useEffect } from 'react';
import Auth from './components/Auth';
import Game from './components/Game';
import api from './services/api';
import './App.css';

/**
 * The root component of the application.
 * It manages the authentication state and renders the appropriate
 * view (Auth or Game) based on whether a user is logged in.
 */
function App() {
  // State to hold the authentication token.
  // It's initialized from localStorage to persist login across sessions.
  const [token, setToken] = useState(localStorage.getItem('token'));

  /**
   * An effect that runs when the component mounts or the token changes.
   * It updates localStorage and sets the default authorization header for all
   * subsequent API requests made with the `api` instance.
   */
  useEffect(() => {
    if (token) {
      // Store the token in localStorage for persistence
      localStorage.setItem('token', token);
      // Set the Authorization header for all future axios requests
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      // If there's no token, remove it from localStorage and the axios headers
      localStorage.removeItem('token');
      delete api.defaults.headers.common['Authorization'];
    }
  }, [token]);

  /**
   * Callback function passed to the Auth component.
   * It's called on successful login or registration to update the app's token state.
   * @param {string} newToken - The JWT received from the backend.
   */
  const handleAuthSuccess = (newToken) => {
    setToken(newToken);
  };

  /**
   * Handles user logout.
   * It clears the token from the state, which triggers the useEffect to
   * clear localStorage and the API headers.
   */
  const handleLogout = () => {
    setToken(null);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Tic-Tac-Toe</h1>
        {token && (
          <button onClick={handleLogout} className="logout-button">
            Logout
          </button>
        )}
      </header>
      <main>
        {token ? (
          <Game />
        ) : (
          <Auth onAuthSuccess={handleAuthSuccess} />
        )}
      </main>
    </div>
  );
}

export default App;