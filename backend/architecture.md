# System Architecture: bosco

## Overview
This architecture outlines a modern, decoupled web application named 'bosco'. It features a React Single-Page Application (SPA) frontend and a Python FastAPI backend. The two services communicate via a RESTful API. The entire application is designed to be containerized using Docker for consistent development and deployment. The backend follows a clean, layered architecture with distinct separation for API endpoints, business logic (CRUD), data models (SQLModel), and data schemas (Pydantic). Authentication is handled using JWT. This design is scalable, maintainable, and follows industry best practices.

## Project Structure
```tree
bosco/
├── backend/src/api/v1/endpoints/
├── backend/src/core/
├── backend/src/crud/
├── backend/src/db/
├── backend/src/models/
├── backend/src/schemas/
├── backend/tests/api/v1/
├── backend/tests/utils/
├── frontend/src/components/
├── frontend/src/contexts/
├── frontend/src/hooks/
├── frontend/src/pages/
└── frontend/src/services/
```

## Build Plan
- **README.md**: Project overview, setup, and deployment instructions.
- **.gitignore**: Specifies intentionally untracked files to ignore.
- **.env.example**: Example environment variables file. Copy to .env and fill in values.
- **docker-compose.yml**: Defines and configures the multi-container Docker application (backend, frontend, database).
- **backend/requirements.txt**: Lists the Python dependencies for the backend service.
- **backend/Dockerfile**: Dockerfile to build the container image for the FastAPI backend.
- **backend/src/core/config.py**: Handles application settings and configuration management by loading environment variables.
- **backend/src/db/session.py**: Manages database connections and sessions using SQLAlchemy.
- **backend/src/db/base.py**: Contains the declarative base for SQLModel models. All models will inherit from this.
- **backend/src/models/user.py**: Defines the User database model using SQLModel.
- **backend/src/models/item.py**: Defines the Item database model, with a foreign key relationship to the User model.
- **backend/src/schemas/token.py**: Pydantic schemas for JWT token data and responses.
- **backend/src/schemas/user.py**: Pydantic schemas for user data validation (create, update, read).
- **backend/src/schemas/item.py**: Pydantic schemas for item data validation (create, update, read).
- **backend/src/core/security.py**: Handles security-related functions like password hashing, password verification, and JWT creation/decoding.
- **backend/src/crud/base.py**: A generic base class with default CRUD (Create, Read, Update, Delete) methods.
- **backend/src/crud/crud_user.py**: Implements specific CRUD operations for the User model.
- **backend/src/crud/crud_item.py**: Implements specific CRUD operations for the Item model.
- **backend/src/api/deps.py**: Manages FastAPI dependencies, such as getting the current user from a token or providing a database session.
- **backend/src/api/v1/endpoints/login.py**: API endpoint for user authentication, token generation, and token testing.
- **backend/src/api/v1/endpoints/users.py**: API endpoints for creating, reading, and managing users.
- **backend/src/api/v1/endpoints/items.py**: API endpoints for creating, reading, and managing items for the authenticated user.
- **backend/src/api/v1/api.py**: Aggregates all the API routers from the 'endpoints' directory into a single main router for version 1 of the API.
- **backend/src/main.py**: The main entry point for the FastAPI application. It initializes the app, sets up CORS middleware, and includes the main API router.
- **frontend/package.json**: Defines frontend project metadata and lists Node.js dependencies (React, Vite, Axios, etc.).
- **frontend/vite.config.js**: Configuration file for the Vite build tool, including server proxy settings to communicate with the backend API.
- **frontend/Dockerfile**: Multi-stage Dockerfile to build the static React assets and serve them using Nginx.
- **frontend/index.html**: The main HTML entry point for the React Single-Page Application.
- **frontend/src/index.css**: Global CSS styles for the application.
- **frontend/src/services/api.js**: Configures an Axios instance for making API requests. It handles setting the base URL and attaching JWT authorization headers.
- **frontend/src/contexts/AuthContext.jsx**: React Context to provide authentication state (user, token) and functions (login, logout) to the entire application.
- **frontend/src/hooks/useAuth.js**: A custom React hook for easily consuming the AuthContext within components.
- **frontend/src/components/PrivateRoute.jsx**: A wrapper for React Router's Route component that redirects unauthenticated users to the login page.
- **frontend/src/pages/LoginPage.jsx**: The component for the user login page, containing the login form.
- **frontend/src/pages/DashboardPage.jsx**: A protected dashboard page component, accessible only after a user has logged in.
- **frontend/src/pages/NotFoundPage.jsx**: A component to display a 404 Not Found error page for invalid routes.
- **frontend/src/App.jsx**: The root component of the React application. It sets up the application's routing structure.
- **frontend/src/main.jsx**: The main entry point for the frontend application. It renders the root App component into the DOM.
