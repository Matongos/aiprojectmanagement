from celery_app import celery_app
from celery.schedules import crontab
from sqlalchemy.orm import Session
from database import SessionLocal
from models.project import Project
from models.task import Task

@celery_app.task
def update_all_metrics():
    """Update metrics for all projects and tasks"""
    db = SessionLocal()
    try:
        projects = db.query(Project).all()
        for project in projects:
            # Update project metrics
            project.update_metrics()
            
            # Update all task metrics in the project
            for task in project.tasks:
                task.update_metrics()
        
        db.commit()
    finally:
        db.close()

# Schedule metrics update every hour
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(minute=0),  # Run every hour
        update_all_metrics.s(),
        name='update-metrics-hourly'
    )

# Schedule metrics update for specific events
@celery_app.task
def update_project_metrics(project_id: int):
    """Update metrics for a specific project"""
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.update_metrics()
            db.commit()
    finally:
        db.close()

@celery_app.task
def update_task_metrics(task_id: int):
    """Update metrics for a specific task"""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.update_metrics()
            # Update parent project metrics as well
            task.project.update_metrics()
            db.commit()
    finally:
        db.close() 