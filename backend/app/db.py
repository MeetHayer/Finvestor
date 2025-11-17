import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.engine import make_url

class Base(DeclarativeBase):
    pass

load_dotenv()

RAW_DSN = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
if not RAW_DSN:
    raise RuntimeError(
        "DATABASE_URL not set! "
        "In Railway: Add a PostgreSQL database service and link it to this service. "
        "Railway will automatically provide DATABASE_URL environment variable."
    )

def _with_driver(dsn: str, driver: str) -> str:
    url = make_url(dsn)
    return str(url.set(drivername=f"postgresql+{driver}"))

SYNC_DSN = _with_driver(RAW_DSN, "psycopg")
ASYNC_DSN = _with_driver(RAW_DSN, "asyncpg")

engine = create_async_engine(ASYNC_DSN, future=True, pool_pre_ping=True)
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