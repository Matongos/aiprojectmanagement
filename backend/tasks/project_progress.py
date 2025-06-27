from celery_app import celery_app
from sqlalchemy.orm import sessionmaker
from database import engine
from models.project import Project
from models.task import Task, TaskState
from models.task_stage import TaskStage
from services.complexity_service import ComplexityService
import logging
from models.notification import Notification
from models.user import User
from models.log_note_attachment import LogNoteAttachment

logger = logging.getLogger(__name__)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task(bind=True)
def calculate_project_progress_task(self, project_id):
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "message": "Project not found"}

        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        if not tasks:
            project.progress = 0
            db.commit()
            return {"success": True, "project_id": project_id, "progress": 0}

        complexity_service = ComplexityService()
        weighted_progress = 0
        total_weight = 0
        completed_tasks = 0
        blocked_tasks = 0
        tasks_progress = []

        for task in tasks:
            try:
                complexity_analysis = complexity_service.analyze_task_complexity(db, task.id)
                if hasattr(complexity_analysis, 'total_score'):
                    complexity_score = complexity_analysis.total_score
                else:
                    complexity_score = 50
            except Exception as e:
                logger.error(f"Error getting complexity for task {task.id}: {str(e)}")
                complexity_score = 50

            time_weight = task.planned_hours if task.planned_hours else 8
            task_weight = (complexity_score / 100) * time_weight
            task_progress = 100 if task.state == TaskState.DONE else task.progress
            weighted_progress += task_progress * task_weight
            total_weight += task_weight
            if task.state == TaskState.DONE:
                completed_tasks += 1
            is_blocked = False
            if task.depends_on:
                incomplete_deps = [dep for dep in task.depends_on if dep.state != TaskState.DONE]
                if incomplete_deps:
                    blocked_tasks += 1
                    is_blocked = True
            stage_name = task.stage.name if task.stage else "No Stage"
            tasks_progress.append({
                "task_id": task.id,
                "name": task.name,
                "progress": task_progress,
                "state": task.state,
                "priority": task.priority,
                "stage": stage_name,
                "is_blocked": is_blocked,
                "complexity_score": complexity_score,
                "planned_hours": time_weight,
                "weight": round(task_weight, 2),
                "assignee": {
                    "id": task.assignee.id,
                    "name": task.assignee.full_name
                } if task.assignee else None
            })

        overall_progress = weighted_progress / total_weight if total_weight > 0 else 0
        project.progress = round(overall_progress, 2)
        db.commit()
        return {"success": True, "project_id": project_id, "progress": round(overall_progress, 2)}
    except Exception as e:
        db.rollback()
        logger.error(f"Error calculating project progress for project {project_id}: {str(e)}")
        return {"success": False, "message": str(e)}
    finally:
        db.close() 