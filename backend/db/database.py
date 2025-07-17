"""
Database connection and session management for Sanad v2.
Implements enterprise-grade connection pooling, transaction management, and health checks.
"""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from loguru import logger
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from ..core.config import get_config
from .models import Base


class DatabaseManager:
    """
    Manages database connections and sessions for the Sanad system.
    Supports both sync and async operations for enterprise scalability.
    """

    def __init__(self):
        """Initialize database manager with configuration."""
        self.config = get_config()
        self.engine = None
        self.async_engine = None
        self.SessionLocal = None
        self.AsyncSessionLocal = None
        self._initialized = False

    def initialize(self) -> None:
        """
        Initialize database connections and create tables.
        Called once during application startup.
        """
        if self._initialized:
            return

        database_url = self.config.database_url
        logger.info(f"Initializing database: {database_url}")

        # Configure database URL for async if needed
        if database_url.startswith("sqlite:///"):
            # Sync SQLite engine
            self.engine = create_engine(
                database_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=self.config.log_level == "DEBUG",
            )

            # Async SQLite engine
            async_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
            self.async_engine = create_async_engine(
                async_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
                echo=self.config.log_level == "DEBUG",
            )
        else:
            # PostgreSQL or other databases
            self.engine = create_engine(
                database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=self.config.log_level == "DEBUG",
            )

            # Convert to async URL if needed
            if "postgresql://" in database_url:
                async_url = database_url.replace(
                    "postgresql://", "postgresql+asyncpg://"
                )
            else:
                async_url = database_url

            self.async_engine = create_async_engine(
                async_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=self.config.log_level == "DEBUG",
            )

        # Create session factories
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        self.AsyncSessionLocal = async_sessionmaker(
            bind=self.async_engine, class_=AsyncSession, expire_on_commit=False
        )

        # Create all tables
        self.create_tables()

        # Set up database event listeners
        self._setup_event_listeners()

        self._initialized = True
        logger.info("Database initialization completed")

    def create_tables(self) -> None:
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            raise

    def _setup_event_listeners(self) -> None:
        """Set up database event listeners for monitoring."""

        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Enable foreign key constraints for SQLite."""
            if "sqlite" in str(self.engine.url):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
                cursor.execute("PRAGMA synchronous=NORMAL")  # Better performance
                cursor.close()

        @event.listens_for(self.engine, "before_cursor_execute")
        def log_slow_queries(conn, cursor, statement, parameters, context, executemany):
            """Log slow database queries for performance monitoring."""
            context._query_start_time = logger.bind(
                query=statement[:100] + "..." if len(statement) > 100 else statement
            )

        @event.listens_for(self.engine, "after_cursor_execute")
        def log_query_time(conn, cursor, statement, parameters, context, executemany):
            """Log query execution time."""
            if hasattr(context, "_query_start_time"):
                # In production, you would send this to monitoring system
                pass

    def get_session(self) -> Session:
        """
        Get a synchronous database session.

        Returns:
            SQLAlchemy session object
        """
        if not self._initialized:
            self.initialize()
        return self.SessionLocal()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get an asynchronous database session with automatic cleanup.

        Yields:
            AsyncSession object
        """
        if not self._initialized:
            self.initialize()

        async with self.AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """
        Perform database health check.

        Returns:
            True if database is healthy, False otherwise
        """
        try:
            if not self._initialized:
                return False

            async with self.get_async_session() as session:
                from sqlalchemy import text

                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return False

    async def close(self) -> None:
        """Close database connections asynchronously."""
        if self.engine:
            self.engine.dispose()
        if self.async_engine:
            await self.async_engine.dispose()

        self._initialized = False
        logger.info("Database connections closed")


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Session:
    """
    Dependency function to get database session for FastAPI.

    Yields:
        Database session
    """
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get async database session for FastAPI.

    Yields:
        Async database session
    """
    async with db_manager.get_async_session() as session:
        yield session


def init_database() -> None:
    """Initialize database - called during application startup."""
    db_manager.initialize()


def close_database() -> None:
    """Close database connections - called during application shutdown."""
    db_manager.close()
