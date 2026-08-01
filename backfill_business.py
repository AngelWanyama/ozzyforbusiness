"""One-time script: give every existing user a business_id (their own id),
mark them as owner, and stamp all their transactions with that business_id.
Safe to run once after the role/business_id migration.
"""
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal as async_session_maker
from app.models.user import User
from app.models.transaction import Transaction


async def run():
    async with async_session_maker() as db:
        users = (await db.execute(select(User))).scalars().all()
        for u in users:
            if u.business_id is None:
                u.business_id = u.id
            if not u.role:
                u.role = "owner"
            # stamp this user's transactions with their business_id
            txns = (await db.execute(
                select(Transaction).where(Transaction.user_id == u.id)
            )).scalars().all()
            for t in txns:
                if t.business_id is None:
                    t.business_id = u.business_id
        await db.commit()
        print(f"Done. Updated {len(users)} user(s) and their transactions.")


if __name__ == "__main__":
    asyncio.run(run())
