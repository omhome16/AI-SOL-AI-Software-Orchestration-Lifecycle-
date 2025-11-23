import axios from 'axios';

/**
 * Creates and configures an Axios instance for making API requests.
 *
 * The base URL for the API is retrieved from environment variables,
 * defaulting to 'http://localhost:8000/api' for local development.
 *
 * An interceptor is attached to automatically include the JWT token
 * from localStorage in the Authorization header of every request.
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

/**
 * Axios request interceptor.
 *
 * This function is executed before each request is sent. It checks for a
 * JWT token in localStorage and, if found, adds it to the request's
 * Authorization header as a Bearer token.
 *
 * @param {object} config - The Axios request configuration.
 * @returns {object} The modified request configuration.
 */
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    // Handle request errors here.
    return Promise.reject(error);
  }
);

/**
 * Axios response interceptor.
 *
 * This can be used to handle global response errors, such as 401 Unauthorized
 * to trigger a logout, or for logging.
 *
 * @param {object} response - The Axios response object.
 * @returns {object} The response object.
 */
api.interceptors.response.use(
  (response) => {
    // Any status code that lie within the range of 2xx cause this function to trigger
    return response;
  },
  (error) => {
    // Any status codes that falls outside the range of 2xx cause this function to trigger
    // For example, we could automatically log out the user on a 401 Unauthorized response.
    if (error.response && error.response.status === 401) {
      // This is where you might clear the token and redirect to the login page.
      // For example:
      // localStorage.removeItem('token');
      // window.location.href = '/login';
      console.error('Unauthorized request - redirecting to login might be needed.');
    }
    return Promise.reject(error);
  }
);


export default api;