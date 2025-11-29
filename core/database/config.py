"""
Database Configuration - Connection management for PostgreSQL.
"""

import os
from typing import Optional
from dataclasses import dataclass
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager

from .models import Base


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    # Database type: "sqlite" or "postgresql"
    db_type: str = "sqlite"
    
    # SQLite settings
    sqlite_path: str = "data/goai_platform.db"
    
    # PostgreSQL settings
    host: str = "localhost"
    port: int = 5432
    database: str = "goai_platform"
    username: str = "goai"
    password: str = "goai_password"
    
    # Pool settings
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False  # SQL logging
    
    @property
    def url(self) -> str:
        """Get SQLAlchemy connection URL."""
        if self.db_type == "sqlite":
            return f"sqlite:///{self.sqlite_path}"
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @property
    def async_url(self) -> str:
        """Get async SQLAlchemy connection URL."""
        if self.db_type == "sqlite":
            return f"sqlite+aiosqlite:///{self.sqlite_path}"
        return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        """Load configuration from environment variables."""
        db_type = os.getenv("DB_TYPE", "sqlite")
        
        return cls(
            db_type=db_type,
            sqlite_path=os.getenv("DB_SQLITE_PATH", "data/goai_platform.db"),
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "goai_platform"),
            username=os.getenv("DB_USER", "goai"),
            password=os.getenv("DB_PASSWORD", "goai_password"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            echo=os.getenv("DB_ECHO", "false").lower() == "true"
        )
    
    @classmethod
    def from_url(cls, url: str) -> "DatabaseConfig":
        """Parse configuration from DATABASE_URL."""
        # Handle DATABASE_URL format
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        
        from urllib.parse import urlparse
        parsed = urlparse(url)
        
        return cls(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            database=parsed.path.lstrip("/"),
            username=parsed.username or "goai",
            password=parsed.password or ""
        )


class Database:
    """Database connection manager."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig.from_env()
        self._engine = None
        self._session_factory = None
    
    @property
    def engine(self):
        """Get or create database engine."""
        if self._engine is None:
            # Create data directory for SQLite
            if self.config.db_type == "sqlite":
                import os
                os.makedirs(os.path.dirname(self.config.sqlite_path) or ".", exist_ok=True)
                self._engine = create_engine(
                    self.config.url,
                    echo=self.config.echo,
                    future=True,
                    connect_args={"check_same_thread": False}  # SQLite thread safety
                )
            else:
                self._engine = create_engine(
                    self.config.url,
                    poolclass=QueuePool,
                    pool_size=self.config.pool_size,
                    max_overflow=self.config.max_overflow,
                    echo=self.config.echo,
                    future=True
                )
        return self._engine
    
    @property
    def session_factory(self):
        """Get session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
        return self._session_factory
    
    def create_tables(self):
        """Create all tables in the database."""
        Base.metadata.create_all(self.engine)
    
    def drop_tables(self):
        """Drop all tables (use with caution!)."""
        Base.metadata.drop_all(self.engine)
    
    @contextmanager
    def session(self) -> Session:
        """Get a database session context manager."""
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session(self) -> Session:
        """Get a new database session (caller must close)."""
        return self.session_factory()
    
    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            from sqlalchemy import text
            with self.session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False
    
    def close(self):
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._session_factory = None


# Global database instance
db = Database()


def get_db() -> Session:
    """Dependency for FastAPI to get database session."""
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()

