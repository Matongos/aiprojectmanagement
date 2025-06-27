from celery import Celery
from sqlalchemy.orm import Session
from database import SessionLocal
from models.user_metrics import UserProductivityMetrics, UserProductivityHistory
from models.user import User
from models.task import Task, TaskState
from models.time_entry import TimeEntry
from services.metrics_service import MetricsService
from datetime import datetime, timedelta, date
from sqlalchemy import or_, and_

celery = Celery('tasks', broker='redis://localhost:6379/0')

@celery.task
async def update_user_productivity(user_id: int):
    """Update productivity metrics for a specific user"""
    db = SessionLocal()
    try:
        # Calculate new metrics
        metrics_service = MetricsService()
        productivity_metrics = await metrics_service.calculate_productivity_score(db, user_id)
        
        # Update or create cached metrics
        metrics = db.query(UserProductivityMetrics).filter(
            UserProductivityMetrics.user_id == user_id
        ).first()
        
        if not metrics:
            metrics = UserProductivityMetrics(user_id=user_id)
            db.add(metrics)
        
        # Update all fields
        metrics.productivity_score = productivity_metrics["overall_score"]
        metrics.completed_tasks = productivity_metrics["completed_tasks"]
        metrics.total_time_spent = productivity_metrics["total_time_spent"]
        metrics.avg_complexity = productivity_metrics["avg_complexity"]
        metrics.task_breakdown = productivity_metrics["task_breakdown"]
        
        db.commit()
        return True
    except Exception as e:
        print(f"Error updating productivity for user {user_id}: {str(e)}")
        return False
    finally:
        db.close()

@celery.task
def update_all_users_productivity():
    """Update productivity metrics for all users"""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            update_user_productivity.delay(user.id)
    finally:
        db.close()

@celery.task
def create_daily_productivity_snapshots():
    """Create daily productivity snapshots for all users"""
    db = SessionLocal()
    try:
        today = date.today()
        
        # Get all users
        users = db.query(User).all()
        
        snapshots_created = 0
        
        for user in users:
            try:
                # Check if snapshot already exists for today
                existing_snapshot = db.query(UserProductivityHistory).filter(
                    UserProductivityHistory.user_id == user.id,
                    UserProductivityHistory.snapshot_date == today,
                    UserProductivityHistory.period_type == "daily"
                ).first()
                
                if existing_snapshot:
                    continue  # Skip if snapshot already exists
                
                # Calculate productivity metrics for today
                start_datetime = datetime.combine(today, datetime.min.time())
                end_datetime = datetime.combine(today, datetime.max.time())
                
                # Get tasks completed today
                completed_tasks = db.query(Task).filter(
                    Task.assigned_to == user.id,
                    Task.state == TaskState.DONE,
                    Task.end_date >= start_datetime,
                    Task.end_date <= end_datetime
                ).all()
                
                # Get tasks started today
                started_tasks = db.query(Task).filter(
                    Task.assigned_to == user.id,
                    Task.created_at >= start_datetime,
                    Task.created_at <= end_datetime
                ).all()
                
                # Get tasks in progress today
                in_progress_tasks = db.query(Task).filter(
                    Task.assigned_to == user.id,
                    Task.state.in_([TaskState.IN_PROGRESS, TaskState.CHANGES_REQUESTED, TaskState.APPROVED]),
                    or_(
                        and_(Task.start_date <= end_datetime, Task.end_date >= start_datetime),
                        and_(Task.start_date.is_(None), Task.created_at <= end_datetime)
                    )
                ).all()
                
                # Calculate time spent today
                time_entries = db.query(TimeEntry).filter(
                    TimeEntry.user_id == user.id,
                    TimeEntry.start_time >= start_datetime,
                    TimeEntry.start_time <= end_datetime
                ).all()
                
                total_time_spent = sum(entry.duration for entry in time_entries)
                
                # Calculate productivity score for today
                productivity_score = 0.0
                avg_complexity = 0.0
                avg_completion_time = 0.0
                
                if completed_tasks:
                    # Calculate average complexity
                    complexity_scores = []
                    completion_times = []
                    
                    for task in completed_tasks:
                        if task.complexity_score:
                            complexity_scores.append(task.complexity_score)
                        
                        if task.start_date and task.end_date:
                            completion_time = (task.end_date - task.start_date).total_seconds() / 3600
                            completion_times.append(completion_time)
                    
                    avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0.0
                    avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0.0
                    
                    # Simple productivity score: (completed_tasks * avg_complexity) / total_time_spent
                    if total_time_spent > 0:
                        productivity_score = (len(completed_tasks) * avg_complexity) / total_time_spent
                
                # Calculate completion rate
                total_active_tasks = len(started_tasks) + len(in_progress_tasks)
                completion_rate = (len(completed_tasks) / total_active_tasks * 100) if total_active_tasks > 0 else 0.0
                
                # Calculate trend compared to previous day
                previous_date = today - timedelta(days=1)
                previous_snapshot = db.query(UserProductivityHistory).filter(
                    UserProductivityHistory.user_id == user.id,
                    UserProductivityHistory.snapshot_date == previous_date,
                    UserProductivityHistory.period_type == "daily"
                ).first()
                
                trend = "stable"
                trend_percentage = 0.0
                
                if previous_snapshot:
                    previous_score = previous_snapshot.productivity_score
                    if previous_score > 0:
                        trend_percentage = ((productivity_score - previous_score) / previous_score) * 100
                        if trend_percentage > 5:
                            trend = "up"
                        elif trend_percentage < -5:
                            trend = "down"
                
                # Create new productivity history record
                new_history = UserProductivityHistory(
                    user_id=user.id,
                    snapshot_date=today,
                    period_type="daily",
                    productivity_score=productivity_score,
                    completed_tasks=len(completed_tasks),
                    total_time_spent=total_time_spent,
                    avg_complexity=avg_complexity,
                    tasks_started=len(started_tasks),
                    tasks_in_progress=len(in_progress_tasks),
                    completion_rate=completion_rate,
                    avg_completion_time=avg_completion_time,
                    score_trend=trend,
                    trend_percentage=trend_percentage
                )
                
                db.add(new_history)
                snapshots_created += 1
                
            except Exception as e:
                print(f"Error creating snapshot for user {user.id}: {str(e)}")
                continue
        
        db.commit()
        print(f"Created {snapshots_created} daily productivity snapshots")
        return snapshots_created
        
    except Exception as e:
        db.rollback()
        print(f"Error creating daily productivity snapshots: {str(e)}")
        return 0
    finally:
        db.close()

# Schedule periodic updates
@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Update all users' productivity every 6 hours
    sender.add_periodic_task(
        21600.0,  # 6 hours in seconds
        update_all_users_productivity.s(),
        name='update-all-productivity'
    ) 