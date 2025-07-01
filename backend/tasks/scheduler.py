from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

# Import the Celery app
from celery_app import celery_app

# Configure periodic tasks for risk data freshness
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Configure periodic tasks for automatic risk data freshness management.
    """
    
    # Refresh all active tasks every 2 hours
    sender.add_periodic_task(
        crontab(minute=0, hour='*/2'),  # Every 2 hours
        schedule_periodic_risk_refresh_task.s(),
        name='refresh-all-task-risks-every-2-hours'
    )
    
    # Refresh high-risk tasks every 30 minutes
    sender.add_periodic_task(
        crontab(minute='*/30'),  # Every 30 minutes
        refresh_high_risk_tasks_task.s(),
        name='refresh-high-risk-tasks-every-30-minutes'
    )
    
    # Refresh critical tasks (risk score >= 80) every 15 minutes
    sender.add_periodic_task(
        crontab(minute='*/15'),  # Every 15 minutes
        refresh_critical_risk_tasks_task.s(),
        name='refresh-critical-risk-tasks-every-15-minutes'
    )

@celery_app.task(bind=True)
def schedule_periodic_risk_refresh_task(self):
    """
    Scheduled task to refresh all active task risks every 2 hours.
    """
    from tasks.analytics import refresh_task_risks_task
    return refresh_task_risks_task.delay(force_refresh=False)

@celery_app.task(bind=True)
def refresh_high_risk_tasks_task(self):
    """
    Scheduled task to refresh high-risk tasks every 30 minutes.
    """
    from tasks.analytics import refresh_task_risks_task
    from database import get_db
    from models.task import Task
    from models.task_risk import TaskRisk
    
    try:
        db = next(get_db())
        
        # Get high-risk tasks (risk score >= 60)
        high_risk_tasks = db.query(Task).join(
            TaskRisk, Task.id == TaskRisk.task_id
        ).filter(
            TaskRisk.risk_score >= 60,
            Task.state.in_(['in_progress', 'approved', 'changes_requested'])
        ).all()
        
        high_risk_task_ids = [task.id for task in high_risk_tasks]
        
        if high_risk_task_ids:
            return refresh_task_risks_task.delay(task_ids=high_risk_task_ids, force_refresh=True)
        else:
            return {
                "status": "success",
                "message": "No high-risk tasks found to refresh",
                "task_id": self.request.id
            }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in refresh_high_risk_tasks_task: {str(e)}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True)
def refresh_critical_risk_tasks_task(self):
    """
    Scheduled task to refresh critical-risk tasks every 15 minutes.
    """
    from tasks.analytics import refresh_task_risks_task
    from database import get_db
    from models.task import Task
    from models.task_risk import TaskRisk
    
    try:
        db = next(get_db())
        
        # Get critical-risk tasks (risk score >= 80)
        critical_risk_tasks = db.query(Task).join(
            TaskRisk, Task.id == TaskRisk.task_id
        ).filter(
            TaskRisk.risk_score >= 80,
            Task.state.in_(['in_progress', 'approved', 'changes_requested'])
        ).all()
        
        critical_risk_task_ids = [task.id for task in critical_risk_tasks]
        
        if critical_risk_task_ids:
            return refresh_task_risks_task.delay(task_ids=critical_risk_task_ids, force_refresh=True)
        else:
            return {
                "status": "success",
                "message": "No critical-risk tasks found to refresh",
                "task_id": self.request.id
            }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in refresh_critical_risk_tasks_task: {str(e)}")
        raise
    finally:
        db.close() 