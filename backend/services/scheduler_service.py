"""Scheduler service for periodic tasks"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from models.task import Task, TaskState
from services.priority_service import PriorityService
from services.priority_scoring_service import PriorityScoringService
from services.notification_service import NotificationService
from database import SessionLocal
import logging
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.notification_service = NotificationService()
        
    async def start(self):
        """Start the scheduler"""
        # Schedule priority updates to run at 00:00 and 12:00 daily
        self.scheduler.add_job(
            self._update_all_task_priorities,
            CronTrigger(hour='0,12'),  # Run at midnight and noon
            id='priority_update',
            name='Update task priorities',
            replace_existing=True,
            misfire_grace_time=3600  # Allow job to run up to 1 hour late if system was down
        )
        
        self.scheduler.start()
        logger.info("Scheduler started - Task priorities will be updated at 00:00 and 12:00 daily")

    async def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    async def _update_all_task_priorities(self):
        """Update priorities for all active tasks"""
        start_time = datetime.now(timezone.utc)
        metrics = {
            "total_tasks": 0,
            "updated_tasks": 0,
            "manual_priority_tasks": 0,
            "errors": 0,
            "priority_changes": {
                "increased": 0,
                "decreased": 0,
                "unchanged": 0
            }
        }
        
        significant_changes: List[Dict] = []  # Track major priority changes for notifications
        
        try:
            db = SessionLocal()
            try:
                # Get all active tasks (not done or canceled)
                active_tasks = db.query(Task).filter(
                    Task.state.notin_(['done', 'canceled'])
                ).all()
                
                metrics["total_tasks"] = len(active_tasks)
                priority_service = PriorityService(db)
                scoring_service = PriorityScoringService(db)
                
                for task in active_tasks:
                    try:
                        # Skip tasks with manual priority
                        if task.priority_source == 'MANUAL':
                            metrics["manual_priority_tasks"] += 1
                            continue
                            
                        # Store original priority for comparison
                        original_priority = task.priority
                        
                        # Calculate new priority
                        result = await priority_service.calculate_priority(task.id)
                        
                        # Update task priority
                        task.priority = result["final_priority"]
                        task.priority_source = result["priority_source"]
                        task.priority_reasoning = result.get("reasoning", [])
                        
                        # Calculate priority score using dedicated scoring service
                        task.priority_score = await scoring_service.calculate_priority_score(task)
                        
                        metrics["updated_tasks"] += 1
                        
                        # Track priority changes
                        if task.priority > original_priority:
                            metrics["priority_changes"]["increased"] += 1
                            # Check for significant increases (e.g., from LOW to URGENT)
                            if self._is_significant_change(original_priority, task.priority):
                                significant_changes.append({
                                    "task_id": task.id,
                                    "task_name": task.name,
                                    "old_priority": original_priority,
                                    "new_priority": task.priority,
                                    "reason": result["reasoning"][0] if result["reasoning"] else "Priority recalculation"
                                })
                        elif task.priority < original_priority:
                            metrics["priority_changes"]["decreased"] += 1
                        else:
                            metrics["priority_changes"]["unchanged"] += 1
                        
                    except Exception as task_error:
                        metrics["errors"] += 1
                        logger.error(f"Error updating priority for task {task.id}: {str(task_error)}")
                        continue
                
                # Commit all changes
                db.commit()
                
                # Send notifications for significant changes
                await self._send_priority_notifications(db, significant_changes)
                
                # Log completion metrics
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                logger.info(
                    f"Priority update completed in {duration:.2f}s. "
                    f"Updated {metrics['updated_tasks']}/{metrics['total_tasks']} tasks. "
                    f"Changes: {metrics['priority_changes']}. "
                    f"Errors: {metrics['errors']}"
                )
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in batch priority update: {str(e)}")
            
    def _is_significant_change(self, old_priority: str, new_priority: str) -> bool:
        """Check if priority change is significant enough for notification"""
        priority_levels = {'LOW': 1, 'NORMAL': 2, 'HIGH': 3, 'URGENT': 4}
        old_level = priority_levels.get(old_priority, 0)
        new_level = priority_levels.get(new_priority, 0)
        return abs(new_level - old_level) > 1  # Notify if change is more than one level
            
    async def _send_priority_notifications(self, db: Session, changes: List[Dict]):
        """Send notifications for significant priority changes"""
        for change in changes:
            try:
                task = db.query(Task).filter(Task.id == change["task_id"]).first()
                if task and task.assigned_to:
                    await self.notification_service.create_notification(
                        db=db,
                        user_id=task.assigned_to,
                        title="Task Priority Change",
                        content=f"Task '{task.name}' priority changed from {change['old_priority']} to {change['new_priority']}. Reason: {change['reason']}",
                        notification_type="priority_change",
                        reference_type="task",
                        reference_id=task.id
                    )
            except Exception as e:
                logger.error(f"Error sending priority change notification: {str(e)}")

scheduler_service = SchedulerService() 