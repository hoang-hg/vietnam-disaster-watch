from app.database import SessionLocal
from app.api import stats_summary
from fastapi import Request
import asyncio

async def test():
    db = SessionLocal()
    try:
        # Mocking or calling the function directly
        # stats_summary(hours: int, date: str | None, db: Session)
        result = stats_summary(hours=24, date=None, db=db)
        print("Result successful:", result)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test())
