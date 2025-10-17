import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
import os

dsn = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
dsn = dsn.replace("postgresql+psycopg", "postgresql+asyncpg")
engine = create_async_engine(dsn, future=True)

async def main():
    async with engine.begin() as conn:
        # create a demo watchlist and portfolio if none
        wl = await conn.execute(text("SELECT id FROM watchlist LIMIT 1"))
        if not wl.first():
            await conn.execute(text("INSERT INTO watchlist (name) VALUES ('Tech Watch')"))
        pf = await conn.execute(text("SELECT id FROM portfolio LIMIT 1"))
        if not pf.first():
            await conn.execute(text("INSERT INTO portfolio (name, inception_date, initial_value) VALUES ('Core', CURRENT_DATE, 10000)"))
    await engine.dispose()

asyncio.run(main())
print("Seed complete.")




