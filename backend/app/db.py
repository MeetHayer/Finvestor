import os
import logging
from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError, InternalError, ProgrammingError, IntegrityError

log = logging.getLogger(__name__)

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

# Configure engine with better error handling
engine = create_async_engine(
    ASYNC_DSN, 
    future=True, 
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False
)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session():
    """Get database session with proper error handling for all SQLAlchemy error types"""
    async with SessionLocal() as session:
        # Ensure pooled connections never remain in aborted state between requests
        try:
            await session.rollback()
        except (OperationalError, InternalError) as e:
            log.warning(f"Database connection issue during rollback: {e}")
            # Connection might be dead, but continue - pool_pre_ping will handle it
        except Exception as e:
            log.debug(f"Non-critical error during rollback: {e}")
        
        try:
            yield session
        except OperationalError as e:
            # Database operation failed (connection lost, hostname not found, etc.)
            log.error(f"OperationalError: Database operation failed - {e}")
            try:
                await session.rollback()
            except Exception:
                pass
            raise HTTPException(
                status_code=503,
                detail=f"Database connection error. Please check Railway database service is linked and running. Error: {str(e)}"
            )
        except InternalError as e:
            # Database internal error (connection dropped, transaction out of sync)
            log.error(f"InternalError: Database internal error - {e}")
            try:
                await session.rollback()
            except Exception:
                pass
            raise HTTPException(
                status_code=503,
                detail=f"Database internal error. Connection may have been dropped. Error: {str(e)}"
            )
        except ProgrammingError as e:
            # Programming error (table not found, syntax error, etc.)
            log.error(f"ProgrammingError: Database programming error - {e}")
            try:
                await session.rollback()
            except Exception:
                pass
            # Check if it's a "table not found" error (migrations not run)
            error_msg = str(e).lower()
            if "does not exist" in error_msg or "relation" in error_msg:
                raise HTTPException(
                    status_code=500,
                    detail=f"Database table not found. Migrations may not have run. Error: {str(e)}"
                )
            raise HTTPException(
                status_code=500,
                detail=f"Database programming error. Check SQL syntax or table structure. Error: {str(e)}"
            )
        except IntegrityError as e:
            # Integrity error (foreign key violation, unique constraint, etc.)
            log.error(f"IntegrityError: Database integrity error - {e}")
            try:
                await session.rollback()
            except Exception:
                pass
            raise HTTPException(
                status_code=400,
                detail=f"Database integrity error. Check foreign keys and constraints. Error: {str(e)}"
            )
        except Exception as e:
            # Any other error
            log.error(f"Unexpected database error: {e}")
            try:
                await session.rollback()
            except Exception:
                pass
            raise