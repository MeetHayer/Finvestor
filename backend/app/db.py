import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


load_dotenv()


def _get_dsn() -> str:
    """
    Retrieve the database connection string from the environment.
    We accept multiple variable names so it works out-of-the-box on Railway,
    Vercel, and local development.
    """
    candidate_keys = [
        "DATABASE_URL",            # Railway, Vercel, Render, etc.
        "RAILWAY_DATABASE_URL",    # Explicit Railway alias
        "DATABASE_PUBLIC_URL",     # Some providers expose this instead
        "POSTGRES_DSN",            # Local .env fallback (last on purpose)
    ]
    for key in candidate_keys:
        value = os.getenv(key)
        if value and value.strip():
            return value.strip()
    raise RuntimeError(
        "No database DSN found. Set POSTGRES_DSN or DATABASE_URL (for Railway you "
        "can reference the Postgres service's DATABASE_URL into the Finvestor service)."
    )


def _ensure_async_driver(dsn: str) -> str:
    # Accept plain postgresql:// or driver-qualified strings and convert to asyncpg.
    if dsn.startswith("postgres://"):
        dsn = dsn.replace("postgres://", "postgresql://", 1)
    if "postgresql+asyncpg" in dsn:
        return dsn
    if "postgresql+psycopg" in dsn:
        return dsn.replace("postgresql+psycopg", "postgresql+asyncpg")
    return dsn.replace("postgresql://", "postgresql+asyncpg://", 1)


DSN = _get_dsn()
ASYNC_DSN = _ensure_async_driver(DSN)

engine = create_async_engine(
    ASYNC_DSN,
    future=True,
    pool_pre_ping=True,
    pool_recycle=3600,
)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session():
    async with SessionLocal() as session:
        # Ensure pooled connections never remain in aborted state between requests
        try:
            await session.rollback()
        except Exception:
            pass
        try:
            yield session
        except Exception:
            # On endpoint error, make sure we roll back before returning connection to pool
            try:
                await session.rollback()
            except Exception:
                pass
            raise
