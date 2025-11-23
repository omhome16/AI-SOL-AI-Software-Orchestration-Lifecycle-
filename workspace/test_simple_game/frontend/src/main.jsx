import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';

/**
 * The main entry point for the React application.
 * This file is responsible for rendering the root component (`App`)
 * into the DOM.
 */

// Find the root DOM element, which is defined in `index.html`.
// This is the container where the entire React application will be mounted.
const rootElement = document.getElementById('root');

// Create a React root for the application.
// This new API is part of React 18 and enables concurrent features.
const root = ReactDOM.createRoot(rootElement);

// Render the application.
// `React.StrictMode` is a tool for highlighting potential problems in an application.
// It activates additional checks and warnings for its descendants and runs only in development mode.
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);