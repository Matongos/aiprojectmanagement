from celery_app import celery_app
from sqlalchemy.orm import sessionmaker
from database import engine
from services.complexity_service import ComplexityService
from models.task import Task
import logging

logger = logging.getLogger(__name__)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task(bind=True)
def calculate_task_complexity_task(self, task_id):
    db = SessionLocal()
    try:
        # Import models here to avoid circular imports
        from models.user import User
        from models.notification import Notification
        from models.log_note_attachment import LogNoteAttachment
        
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"success": False, "message": "Task not found"}
        
        complexity_service = ComplexityService()
        import asyncio
        complexity = asyncio.run(complexity_service.analyze_task_complexity(db, task_id))
        
        task.complexity_score = complexity.total_score
        task.complexity_factors = {
            "technical": complexity.factors.technical_complexity,
            "scope": complexity.factors.scope_complexity,
            "time_pressure": complexity.factors.time_pressure,
            "environmental": complexity.factors.environmental_complexity,
            "dependencies": complexity.factors.dependencies_impact,
            "summary": complexity.analysis_summary
        }
        task.complexity_last_updated = complexity.last_updated
        db.commit()
        return {"success": True, "task_id": task_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Error calculating complexity for task {task_id}: {str(e)}")
        return {"success": False, "message": str(e)}
    finally:
        db.close() 