from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from typing import Dict, List
from models.time_entry import TimeEntry
from models.task import Task, TaskState

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_productivity(self, user_id: int) -> Dict:
        """
        Calculate user productivity metrics using basic fields
        """
        try:
            # Get current date and start of week/month
            current_date = datetime.utcnow().date()
            start_of_week = current_date - timedelta(days=current_date.weekday())
            start_of_month = current_date.replace(day=1)

            # Calculate basic metrics
            total_time_entries = self.db.query(TimeEntry).filter(
                TimeEntry.user_id == user_id
            ).count()

            total_duration = self.db.query(func.sum(TimeEntry.duration)).filter(
                TimeEntry.user_id == user_id
            ).scalar() or 0

            billable_duration = self.db.query(func.sum(TimeEntry.duration)).filter(
                TimeEntry.user_id == user_id,
                TimeEntry.is_billable == True
            ).scalar() or 0

            # Get task completion metrics
            completed_tasks = self.db.query(Task).filter(
                Task.assigned_to == user_id,
                Task.state == TaskState.DONE
            ).count()

            total_tasks = self.db.query(Task).filter(
                Task.assigned_to == user_id
            ).count()

            # Calculate simple metrics
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            billable_rate = (billable_duration / total_duration * 100) if total_duration > 0 else 0
            avg_duration_per_entry = total_duration / total_time_entries if total_time_entries > 0 else 0

            return {
                "summary": {
                    "total_hours_logged": round(total_duration, 2),
                    "billable_hours": round(billable_duration, 2),
                    "billable_percentage": round(billable_rate, 2),
                    "average_hours_per_entry": round(avg_duration_per_entry, 2)
                },
                "task_metrics": {
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "completion_rate": round(completion_rate, 2)
                },
                "performance_indicators": [
                    {
                        "type": "positive" if completion_rate >= 70 else "negative",
                        "message": "Good task completion rate" if completion_rate >= 70 else "Task completion needs improvement",
                        "value": f"{round(completion_rate)}%"
                    },
                    {
                        "type": "positive" if billable_rate >= 80 else "warning",
                        "message": "Good billable hours ratio" if billable_rate >= 80 else "Consider increasing billable hours",
                        "value": f"{round(billable_rate)}%"
                    }
                ]
            }
        except Exception as e:
            print(f"Error calculating user productivity: {str(e)}")
            raise 