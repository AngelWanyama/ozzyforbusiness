import asyncio
import sys
from app.core.database import AsyncSessionLocal
from app.services.summary_generator import summary_generator

async def run_summaries(summary_type: str):
    async with AsyncSessionLocal() as session:
        if summary_type == "daily":
            await summary_generator.generate_daily_summaries(session)
        elif summary_type == "weekly":
            await summary_generator.generate_weekly_summaries(session)
        elif summary_type == "monthly":
            await summary_generator.generate_monthly_summaries(session)
        else:
            print(f"Unknown summary type: {summary_type}")
            return
    print(f"Successfully generated {summary_type} summaries.")

if __name__ == "__main__":
    s_type = sys.argv[1] if len(sys.argv) > 1 else "daily"
    asyncio.run(run_summaries(s_type))
