import asyncio
from .db import engine, Base
from . import models  # Import all models to register them with Base.metadata

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(main())

