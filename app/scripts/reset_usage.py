import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import update

async def reset_monthly_usage():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Reset all users' monthly transaction counts
            stmt = update(User).values(transactions_this_month=0)
            await session.execute(stmt)
        print("Successfully reset monthly usage for all users.")

if __name__ == "__main__":
    asyncio.run(reset_monthly_usage())
