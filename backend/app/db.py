import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DSN = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
if not DSN:
    raise RuntimeError("POSTGRES_DSN/DATABASE_URL not set")

ASYNC_DSN = DSN.replace("postgresql+psycopg", "postgresql+asyncpg")

engine = create_async_engine(ASYNC_DSN, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session():
    async with SessionLocal() as session:
        yield session