import asyncio
from app.services.seed_one_year import seed_one_year
if __name__ == "__main__":
    asyncio.run(seed_one_year())

