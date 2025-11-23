"""
Main entry point for the FastAPI application.

This module initializes the FastAPI application, configures CORS middleware,
and includes the API routers for different parts of the application like
user management and game logic.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import users, game

# Define the API version prefix
API_V1_STR = "/api/v1"

# Initialize the FastAPI application instance
# The title and openapi_url are set for documentation purposes.
app = FastAPI(
    title="Test Simple Game API",
    description="API for a simple Tic-Tac-Toe game.",
    version="1.0.0",
    openapi_url=f"{API_V1_STR}/openapi.json"
)

# Define the list of allowed origins for CORS.
# This should be configured securely for production environments,
# typically by reading from environment variables.
# For this project, we allow common local development origins.
origins = [
    "http://localhost",
    "http://localhost:3000",  # Common port for create-react-app
    "http://localhost:5173",  # Default port for Vite
]

# Add CORS (Cross-Origin Resource Sharing) middleware to the application.
# This allows the frontend, which is served from a different origin (domain/port),
# to make requests to this backend API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # Allows cookies to be included in requests
    allow_methods=["*"],      # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],      # Allows all request headers
)

# Include the API routers into the main application.
# This organizes the application's endpoints into logical modules.

# The users router handles user registration and authentication (login).
app.include_router(users.router, prefix=f"{API_V1_STR}/users", tags=["Users"])

# The game router handles all game-related logic, such as starting a game,
# getting the game state, and making moves.
# The prefix from the router itself ("/game") will be appended to this prefix.
app.include_router(game.router, prefix=API_V1_STR, tags=["Game"])


@app.get("/", summary="Health Check", tags=["Root"])
def read_root():
    """
    Root endpoint to provide a basic health check.

    This endpoint can be used by monitoring services to verify that the
    application is running and responsive.

    Returns:
        dict: A simple JSON response indicating the status.
    """
    return {"status": "ok", "message": "Welcome to the Simple Game API!"}