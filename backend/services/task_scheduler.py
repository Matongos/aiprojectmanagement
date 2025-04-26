import threading
import time
import schedule
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from models.tasks import Task
from services.notification_service import NotificationService
from database import SessionLocal

class TaskScheduler:
    """Class for running scheduled tasks."""
    
    @staticmethod
    def start_scheduler():
        """Start the scheduler in a separate thread."""
        scheduler_thread = threading.Thread(target=TaskScheduler._run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        print("Task scheduler started in background thread")
        
    @staticmethod
    def _run_scheduler():
        """Run the scheduler."""
        # Schedule tasks
        schedule.every().day.at("09:00").do(TaskScheduler.check_due_dates)
        
        # Run the scheduler loop
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                print(f"Error in scheduler: {str(e)}")
                time.sleep(300)  # Wait 5 minutes before retrying
    
    @staticmethod
    def check_due_dates():
        """Check for tasks with approaching due dates and send notifications."""
        print("Running scheduled task: checking due dates")
        db = SessionLocal()
        try:
            today = datetime.utcnow().date()
            tomorrow = today + timedelta(days=1)
            next_week = today + timedelta(days=7)
            
            # Get tasks due tomorrow
            due_tomorrow = (
                db.query(Task)
                .filter(
                    Task.due_date.between(
                        datetime.combine(tomorrow, datetime.min.time()),
                        datetime.combine(tomorrow, datetime.max.time())
                    ),
                    Task.status != "done",
                    Task.status != "cancelled"
                )
                .all()
            )
            
            # Get tasks due within the next week
            due_next_week = (
                db.query(Task)
                .filter(
                    Task.due_date.between(
                        datetime.combine(tomorrow + timedelta(days=1), datetime.min.time()),
                        datetime.combine(next_week, datetime.max.time())
                    ),
                    Task.status != "done",
                    Task.status != "cancelled"
                )
                .all()
            )
            
            # Send notifications for tasks due tomorrow
            for task in due_tomorrow:
                if task.assignee_id:
                    NotificationService.notify_due_date_approaching(
                        db=db,
                        task_id=task.id,
                        task_title=task.title,
                        days_remaining=1,
                        user_id=task.assignee_id
                    )
            
            # Send notifications for tasks due within the next week
            for task in due_next_week:
                if task.assignee_id:
                    days_remaining = (task.due_date.date() - today).days
                    NotificationService.notify_due_date_approaching(
                        db=db,
                        task_id=task.id,
                        task_title=task.title,
                        days_remaining=days_remaining,
                        user_id=task.assignee_id
                    )
            
            print(f"Sent notifications for {len(due_tomorrow)} tasks due tomorrow and {len(due_next_week)} tasks due next week")
            db.commit()
            
        except Exception as e:
            print(f"Error checking due dates: {str(e)}")
            db.rollback()
        finally:
            db.close() 