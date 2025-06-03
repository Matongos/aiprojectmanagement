from celery import Celery
from sqlalchemy.orm import Session
from database import SessionLocal
from models.user_metrics import UserProductivityMetrics
from models.user import User
from services.metrics_service import MetricsService

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

# Schedule periodic updates
@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Update all users' productivity every 6 hours
    sender.add_periodic_task(
        21600.0,  # 6 hours in seconds
        update_all_users_productivity.s(),
        name='update-all-productivity'
    ) 