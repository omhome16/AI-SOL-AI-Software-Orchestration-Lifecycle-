"""
Database configuration and session management for the application.

This module sets up the SQLAlchemy engine, session factory, and the declarative base
for ORM models. It reads the database connection string from the application's
settings.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# The database engine is the entry point to the database.
# It's configured with the database URL from the settings.
# For SQLite, `connect_args={"check_same_thread": False}` is needed because
# SQLite by default only allows one thread to communicate with it, assuming
# that each thread would be a different request. FastAPI can use multiple
# threads for a single request, so this argument is necessary to allow that.
engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False}
)

# The SessionLocal class is a factory for creating new Session objects.
# A Session object is the handle for all database operations.
# `autocommit=False` and `autoflush=False` are standard settings for using
# sessions with FastAPI, where we want to manually control the transaction
# lifecycle within each request.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# The Base class is a declarative base that our ORM models will inherit from.
# SQLAlchemy uses this base class to map the Python classes to database tables.
Base = declarative_base()

# Dependency to get a DB session.
# This will be used in path operation functions to get a database session.
# It ensures that the database connection is opened at the start of a request
# and closed at the end, even if an error occurs.
def get_db():
    """
    A dependency function that provides a database session for a request.

    Yields:
        sqlalchemy.orm.Session: The database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()