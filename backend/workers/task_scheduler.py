import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from services.scheduled_tasks import ScheduledTaskService

async def check_task_states():
    """
    Background worker that periodically checks and updates task states
    based on their scheduled start dates.
    """
    while True:
        try:
            db = SessionLocal()
            try:
                ScheduledTaskService.update_task_states(db)
            finally:
                db.close()
                
            # Wait for 1 minute before next check
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"Error in task scheduler: {str(e)}")
            # Wait for 5 seconds before retrying on error
            await asyncio.sleep(5)

async def start_scheduler():
    """Start the task scheduler background worker"""
    await check_task_states() 