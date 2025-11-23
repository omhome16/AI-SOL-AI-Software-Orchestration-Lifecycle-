import React, { useState } from 'react';
import PropTypes from 'prop-types';
import api from '../services/api';

/**
 * Auth component for user registration and login.
 * It provides a form to enter credentials and communicates with the backend API.
 * On successful authentication, it stores the JWT and notifies the parent component.
 *
 * @param {object} props - The component props.
 * @param {function} props.onAuthSuccess - Callback function executed on successful login/registration.
 */
const Auth = ({ onAuthSuccess }) => {
  // State to toggle between Login and Register views
  const [isLoginView, setIsLoginView] = useState(true);

  // State for form inputs
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  // State for handling loading and errors
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Toggles the view between the login and registration forms.
   * Clears form fields and errors when switching.
   */
  const toggleView = () => {
    setIsLoginView(!isLoginView);
    setError(null);
    setUsername('');
    setPassword('');
  };

  /**
   * Handles the form submission for both login and registration.
   * It sends a request to the appropriate API endpoint and handles the response.
   * @param {React.FormEvent<HTMLFormElement>} e - The form submission event.
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let response;
      if (isLoginView) {
        // FastAPI's default OAuth2 password flow expects form data, not JSON.
        // We use URLSearchParams to construct the body and set the correct header.
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        response = await api.post('/token', formData, {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        });
      } else {
        // The registration endpoint expects a standard JSON payload.
        response = await api.post('/users/register', { username, password });
      }

      // The backend should return an access_token on both successful login and registration.
      const token = response.data.access_token;
      if (token) {
        localStorage.setItem('token', token);
        // The api instance's interceptor will now automatically add this token to future requests.
        // Notify the parent component that authentication was successful.
        onAuthSuccess();
      } else {
        // This case should ideally not be reached if the backend is consistent.
        throw new Error('Authentication failed: No token received from server.');
      }
    } catch (err) {
      // Extract a user-friendly error message from the API response if available.
      const errorMessage = err.response?.data?.detail || err.message || 'An unexpected error occurred.';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container" style={styles.container}>
      <h2 style={styles.header}>{isLoginView ? 'Login' : 'Register'}</h2>
      <form onSubmit={handleSubmit} style={styles.form}>
        <div className="form-group" style={styles.formGroup}>
          <label htmlFor="username" style={styles.label}>Username</label>
          <input
            type="text"
            id="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={loading}
            style={styles.input}
          />
        </div>
        <div className="form-group" style={styles.formGroup}>
          <label htmlFor="password" style={styles.label}>Password</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={loading}
            style={styles.input}
          />
        </div>
        {error && <p style={styles.errorMessage}>{error}</p>}
        <button type="submit" disabled={loading} style={styles.button}>
          {loading ? 'Submitting...' : (isLoginView ? 'Login' : 'Register')}
        </button>
      </form>
      <p style={styles.toggleText}>
        {isLoginView ? "Don't have an account?" : 'Already have an account?'}
        <button type="button" onClick={toggleView} style={styles.toggleButton}>
          {isLoginView ? 'Register' : 'Login'}
        </button>
      </p>
    </div>
  );
};

// Prop-types for type checking and ensuring onAuthSuccess is passed.
Auth.propTypes = {
  onAuthSuccess: PropTypes.func.isRequired,
};

// Basic styling to make the component usable out-of-the-box.
const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    maxWidth: '400px',
    margin: '40px auto',
    padding: '2rem',
    border: '1px solid #ccc',
    borderRadius: '8px',
    boxShadow: '0 4px 8px rgba(0,0,0,0.1)',
  },
  header: {
    marginBottom: '1.5rem',
  },
  form: {
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
  },
  formGroup: {
    marginBottom: '1rem',
  },
  label: {
    display: 'block',
    marginBottom: '0.5rem',
    fontWeight: 'bold',
  },
  input: {
    width: '100%',
    padding: '0.75rem',
    border: '1px solid #ccc',
    borderRadius: '4px',
    boxSizing: 'border-box',
  },
  button: {
    padding: '0.75rem',
    border: 'none',
    borderRadius: '4px',
    backgroundColor: '#007bff',
    color: 'white',
    fontSize: '1rem',
    cursor: 'pointer',
    marginTop: '0.5rem',
  },
  errorMessage: {
    color: 'red',
    textAlign: 'center',
    marginBottom: '1rem',
  },
  toggleText: {
    marginTop: '1.5rem',
  },
  toggleButton: {
    background: 'none',
    border: 'none',
    color: '#007bff',
    cursor: 'pointer',
    marginLeft: '0.5rem',
    textDecoration: 'underline',
    fontSize: '1rem',
  },
};

export default Auth;