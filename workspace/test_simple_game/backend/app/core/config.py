import os
from typing import List, Union

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """
    PROJECT_NAME: str = "Tic-Tac-Toe Game API"
    API_V1_STR: str = "/api/v1"

    # Security settings
    # To generate a good secret key, run: openssl rand -hex 32
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database settings
    # The default URI points to a local SQLite file.
    # For production, you might want to use PostgreSQL or another database.
    # Example for PostgreSQL: "postgresql+asyncpg://user:password@host:port/db"
    # Example for SQLite async: "sqlite+aiosqlite:///./test.db"
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./test.db"

    # CORS (Cross-Origin Resource Sharing) settings
    # A list of origins that should be permitted to make cross-origin requests.
    # e.g., ["http://localhost:3000", "http://localhost:5173"]
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode='before')
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """
        Parses a comma-separated string of origins from environment variables
        into a list of strings.
        """
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Pydantic-settings configuration
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.env")
    )


# Create a single, reusable instance of the settings
settings = Settings()