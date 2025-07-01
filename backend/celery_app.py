from celery import Celery

# Create the Celery app
celery_app = Celery(
    'aiprojectmanagement',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=[
        'tasks.task_complexity',
        'tasks.metrics_updater',
        'tasks.productivity_updater',
        'tasks.task_priority',
        'tasks.project_progress',
        'tasks.task_risk',
        'tasks.analytics',
    ]
)

# Optional: Configure Celery settings
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
) 