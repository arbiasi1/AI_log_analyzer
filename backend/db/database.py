import os
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv(override=True)


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=1)
def get_database_url() -> str | None:
    return os.getenv("DATABASE_URL")


@lru_cache(maxsize=1)
def get_engine():
    database_url = get_database_url()
    if not database_url:
        return None
    return create_engine(database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_session_factory():
    engine = get_engine()
    if engine is None:
        return None
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> bool:
    engine = get_engine()
    if engine is None:
        return False

    import backend.db.models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
        return True
    except SQLAlchemyError as exc:
        print(f"PostgreSQL initialization failed, using memory storage fallback: {exc}")
        return False


def database_enabled() -> bool:
    return get_engine() is not None


def database_connected() -> bool:
    engine = get_engine()
    if engine is None:
        return False

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
