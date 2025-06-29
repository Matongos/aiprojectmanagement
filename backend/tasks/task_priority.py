from celery_app import celery_app
from sqlalchemy.orm import sessionmaker
from database import engine
from services.priority_scoring_service import PriorityScoringService
from models.task import Task
import logging

logger = logging.getLogger(__name__)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task(bind=True)
def calculate_task_priority_score_task(self, task_id):
    db = SessionLocal()
    try:
        # Import models here to avoid circular imports
        from models.user import User
        from models.notification import Notification
        from models.log_note_attachment import LogNoteAttachment
        
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"success": False, "message": "Task not found"}
        
        # Check if task is completed or cancelled
        if task.state in ['done', 'cancelled']:
            return {
                "success": True,
                "task_id": task_id,
                "score": 0,
                "score_breakdown": {
                    "priority_score": 0,
                    "complexity_score": 0
                },
                "explanation": f"Task is {task.state}, priority calculation not needed",
                "status": f"Task is {task.state}",
                "priority_reasoning": [f"Task is {task.state}"]
            }
        
        # Verify required fields
        missing_fields = []
        if not task.name:
            missing_fields.append("name")
        if not task.priority:
            missing_fields.append("priority level")
            
        if missing_fields:
            return {
                "success": False,
                "message": f"Missing required fields for scoring: {', '.join(missing_fields)}"
            }
        
        # Calculate priority score (80% weight)
        priority_weights = {
            'low': 20,
            'normal': 40,
            'high': 60,
            'urgent': 80
        }
        priority_score = priority_weights.get(task.priority.lower(), 40)  # Default to normal if unknown
        
        # Get stored task complexity (20% weight) - use stored data instead of recalculating
        if task.complexity_score is not None and task.complexity_score > 0:
            # Use stored complexity score, convert to 20% scale
            complexity_score = (task.complexity_score / 100) * 20
            complexity_source = "stored"
        else:
            # Fallback to default if no stored complexity
            complexity_score = 10  # Default to medium complexity (50% of 20)
            complexity_source = "default"
            logger.warning(f"No stored complexity found for task {task.id}, using default")
        
        # Calculate total score
        total_score = priority_score + complexity_score
        
        # Generate explanation
        priority_level = task.priority.lower()
        explanation_parts = [
            f"Task priority is {priority_level} ({priority_score}% weight)",
            f"Task complexity score adds {complexity_score:.1f}% weight (from {complexity_source} data)"
        ]
        
        if hasattr(task, 'dependent_tasks') and task.dependent_tasks:
            explanation_parts.append(f"Task is blocking {len(task.dependent_tasks)} other tasks")
        
        if task.deadline:
            from datetime import datetime, timezone
            days_to_deadline = (task.deadline - datetime.now(timezone.utc)).days
            if days_to_deadline < 0:
                explanation_parts.append(f"Task is overdue by {abs(days_to_deadline)} days")
            elif days_to_deadline < 7:
                explanation_parts.append(f"Task deadline is in {days_to_deadline} days")
        
        # Update task priority reasoning
        task.priority_reasoning = explanation_parts
        
        # Update the task with new score
        task.priority_score = total_score
        
        # Invalidate any cached priority data
        from services.priority_service import PriorityService
        priority_service = PriorityService(db)
        priority_service.invalidate_cache(task_id)
        
        # Commit changes to database
        db.commit()
        
        return {
            "success": True,
            "task_id": task_id,
            "score": total_score,
            "score_breakdown": {
                "priority_score": priority_score,
                "complexity_score": complexity_score
            },
            "explanation": f"Priority score calculated successfully using {complexity_source} complexity data",
            "status": "completed",
            "priority_reasoning": explanation_parts,
            "complexity_source": complexity_source
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error calculating priority score for task {task_id}: {str(e)}")
        return {"success": False, "message": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True)
def auto_set_task_priority_task(self, task_id):
    """
    Automatically calculate and set task priority using rules and AI.
    
    The priority is determined by:
    1. First applying rule-based logic for common cases
    2. Using AI for more nuanced decisions when rules are inconclusive
    3. Respecting manual priority if set
    """
    db = SessionLocal()
    try:
        # Import models here to avoid circular imports
        from models.user import User
        from models.notification import Notification
        from models.log_note_attachment import LogNoteAttachment
        
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"success": False, "message": "Task not found"}
        
        # Import services
        from services.priority_service import PriorityService
        from services.priority_scoring_service import PriorityScoringService
        
        # Calculate priority using AI and rules
        priority_service = PriorityService(db)
        import asyncio
        result = asyncio.run(priority_service.calculate_priority(task_id))
        
        # Update task priority if not manually set
        if result["priority_source"] != "MANUAL":
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                # Update priority fields
                task.priority = result["final_priority"]
                task.priority_source = result["priority_source"]
                task.priority_reasoning = result.get("reasoning", [])
                
                # Calculate priority score using dedicated scoring service
                scoring_service = PriorityScoringService(db)
                task.priority_score = asyncio.run(scoring_service.calculate_priority_score(task))
                
                db.commit()
        
        return {
            "success": True,
            "task_id": task_id,
            "result": result
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error auto-setting priority for task {task_id}: {str(e)}")
        return {"success": False, "message": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True)
def update_all_task_priorities_task(self):
    """
    Update priorities for all active tasks using background processing.
    
    This task:
    1. Gets all active tasks (not done or canceled)
    2. Updates their priorities using rules and AI
    3. Calculates priority scores
    4. Sends notifications for significant changes
    5. Returns detailed metrics
    """
    db = SessionLocal()
    try:
        # Import models here to avoid circular imports
        from models.user import User
        from models.notification import Notification
        from models.log_note_attachment import LogNoteAttachment
        from models.task import Task, TaskState
        from services.priority_service import PriorityService
        from services.priority_scoring_service import PriorityScoringService
        from datetime import datetime, timezone
        from typing import Dict, List
        
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
            # Get all active tasks (not done or canceled)
            active_tasks = db.query(Task).filter(
                Task.state.notin_(['done', 'canceled'])
            ).all()
            
            metrics["total_tasks"] = len(active_tasks)
            priority_service = PriorityService(db)
            scoring_service = PriorityScoringService(db)
            
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 0,
                    'total': len(active_tasks),
                    'status': f'Processing {len(active_tasks)} tasks...'
                }
            )
            
            for i, task in enumerate(active_tasks):
                try:
                    # Update progress every 10 tasks
                    if i % 10 == 0:
                        self.update_state(
                            state='PROGRESS',
                            meta={
                                'current': i,
                                'total': len(active_tasks),
                                'status': f'Processing task {i+1}/{len(active_tasks)}: {task.name}'
                            }
                        )
                    
                    # Skip tasks with manual priority
                    if hasattr(task, 'priority_source') and task.priority_source == 'MANUAL':
                        metrics["manual_priority_tasks"] += 1
                        continue
                        
                    # Store original priority for comparison
                    original_priority = task.priority
                    
                    # Calculate new priority using async function
                    import asyncio
                    result = asyncio.run(priority_service.calculate_priority(task.id))
                    
                    # Update task priority
                    task.priority = result["final_priority"]
                    task.priority_source = result["priority_source"]
                    task.priority_reasoning = result.get("reasoning", [])
                    
                    # Calculate priority score using dedicated scoring service
                    task.priority_score = asyncio.run(scoring_service.calculate_priority_score(task))
                    
                    metrics["updated_tasks"] += 1
                    
                    # Track priority changes
                    if task.priority > original_priority:
                        metrics["priority_changes"]["increased"] += 1
                        # Check for significant increases (e.g., from LOW to URGENT)
                        if _is_significant_change(original_priority, task.priority):
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
            
            # Create notifications for significant changes (directly using model)
            for change in significant_changes:
                try:
                    task = db.query(Task).filter(Task.id == change["task_id"]).first()
                    if task and task.assigned_to:
                        # Create notification directly using the model
                        notification = Notification(
                            user_id=task.assigned_to,
                            title="Task Priority Change",
                            content=f"Task '{task.name}' priority changed from {change['old_priority']} to {change['new_priority']}. Reason: {change['reason']}",
                            type="priority_change",
                            reference_type="task",
                            reference_id=task.id,
                            created_at=datetime.now(timezone.utc)
                        )
                        db.add(notification)
                except Exception as e:
                    logger.error(f"Error creating priority change notification: {str(e)}")
            
            # Commit notifications
            db.commit()
            
            # Log completion metrics
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Priority update completed in {duration:.2f}s. "
                f"Updated {metrics['updated_tasks']}/{metrics['total_tasks']} tasks. "
                f"Changes: {metrics['priority_changes']}. "
                f"Errors: {metrics['errors']}"
            )
            
            return {
                "success": True,
                "metrics": metrics,
                "duration_seconds": duration,
                "significant_changes": significant_changes,
                "status": "completed"
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error in batch priority update: {str(e)}")
            return {"success": False, "message": str(e)}
            
    except Exception as e:
        logger.error(f"Error in update_all_task_priorities_task: {str(e)}")
        return {"success": False, "message": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True)
def scheduled_priority_score_update_task(self):
    """
    Scheduled task that runs every 3 hours to update priority scores for all active tasks.
    Uses stored complexity data and current priority levels.
    """
    db = SessionLocal()
    try:
        from models.task import Task, TaskState
        from datetime import datetime, timezone
        from typing import Dict, List
        
        start_time = datetime.now(timezone.utc)
        metrics = {
            "total_tasks": 0,
            "updated_tasks": 0,
            "errors": 0,
            "tasks_with_complexity": 0,
            "tasks_without_complexity": 0
        }
        
        try:
            # Get all active tasks (not done or canceled)
            active_tasks = db.query(Task).filter(
                Task.state.notin_(['done', 'canceled'])
            ).all()
            
            metrics["total_tasks"] = len(active_tasks)
            
            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 0,
                    'total': len(active_tasks),
                    'status': f'Updating priority scores for {len(active_tasks)} tasks...'
                }
            )
            
            for i, task in enumerate(active_tasks):
                try:
                    # Update progress every 10 tasks
                    if i % 10 == 0:
                        self.update_state(
                            state='PROGRESS',
                            meta={
                                'current': i,
                                'total': len(active_tasks),
                                'status': f'Processing task {i+1}/{len(active_tasks)}: {task.name}'
                            }
                        )
                    
                    # Skip tasks without required fields
                    if not task.name or not task.priority:
                        continue
                    
                    # Calculate priority score using stored complexity
                    priority_weights = {
                        'low': 20,
                        'normal': 40,
                        'high': 60,
                        'urgent': 80
                    }
                    priority_score = priority_weights.get(task.priority.lower(), 40)
                    
                    # Use stored complexity if available
                    if task.complexity_score is not None and task.complexity_score > 0:
                        complexity_score = (task.complexity_score / 100) * 20
                        metrics["tasks_with_complexity"] += 1
                    else:
                        complexity_score = 10  # Default to medium complexity
                        metrics["tasks_without_complexity"] += 1
                    
                    # Calculate total score
                    total_score = priority_score + complexity_score
                    
                    # Update task priority score
                    task.priority_score = total_score
                    
                    metrics["updated_tasks"] += 1
                    
                except Exception as task_error:
                    metrics["errors"] += 1
                    logger.error(f"Error updating priority score for task {task.id}: {str(task_error)}")
                    continue
            
            # Commit all changes
            db.commit()
            
            # Log completion metrics
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.info(
                f"Scheduled priority score update completed in {duration:.2f}s. "
                f"Updated {metrics['updated_tasks']}/{metrics['total_tasks']} tasks. "
                f"Tasks with complexity: {metrics['tasks_with_complexity']}, "
                f"Tasks without complexity: {metrics['tasks_without_complexity']}. "
                f"Errors: {metrics['errors']}"
            )
            
            return {
                "success": True,
                "metrics": metrics,
                "duration_seconds": duration,
                "status": "completed"
            }
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error in scheduled priority score update: {str(e)}")
            return {"success": False, "message": str(e)}
            
    except Exception as e:
        logger.error(f"Error in scheduled_priority_score_update_task: {str(e)}")
        return {"success": False, "message": str(e)}
    finally:
        db.close()

def _is_significant_change(old_priority: str, new_priority: str) -> bool:
    """Check if priority change is significant enough for notification"""
    priority_levels = {'LOW': 1, 'NORMAL': 2, 'HIGH': 3, 'URGENT': 4}
    old_level = priority_levels.get(old_priority, 0)
    new_level = priority_levels.get(new_priority, 0)
    return abs(new_level - old_level) > 1  # Notify if change is more than one level 

@celery_app.task(bind=True)
def calculate_task_time_risk_task(self, task_id):
    """
    Calculate time-based risk for a task using Celery background processing.
    
    The risk is calculated using the formula:
    Risk (%) = (T_alloc / (T_left + ε)) * 100
    
    Where:
    - T_alloc = allocated/planned hours for the task
    - T_left = time left until deadline (in hours)
    - ε = small number (1) to avoid division by zero
    
    The risk increases when T_left is small and can exceed 100% to show true severity.
    """
    db = SessionLocal()
    try:
        # Import models here to avoid circular imports
        from models.user import User
        from models.notification import Notification
        from models.log_note_attachment import LogNoteAttachment
        from datetime import datetime, timezone, timedelta
        from services.redis_service import get_redis_client
        
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {"success": False, "message": "Task not found"}
        
        # Get current time with timezone awareness
        now = datetime.now(timezone.utc)
        
        # Get task time data
        allocated_hours = task.planned_hours or 0
        start_date = task.start_date
        deadline = task.deadline
        
        # Ensure timezone awareness for datetime objects
        def make_timezone_aware(dt):
            if dt is None:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        
        start_date = make_timezone_aware(start_date)
        deadline = make_timezone_aware(deadline)
        
        # Calculate time left until deadline (in hours)
        if not deadline:
            time_left_hours = 0
            is_overdue = False
            overdue_hours = 0
        else:
            time_left = deadline - now
            time_left_hours = max(0, time_left.total_seconds() / 3600)
            is_overdue = time_left.total_seconds() < 0
            overdue_hours = abs(time_left.total_seconds() / 3600) if is_overdue else 0
        
        # Calculate time passed since start (in hours)
        time_passed_hours = 0
        if start_date:
            time_passed = now - start_date
            time_passed_hours = max(0, time_passed.total_seconds() / 3600)
        
        # Calculate total time available (from start to deadline)
        total_time_hours = 0
        if start_date and deadline:
            total_time = deadline - start_date
            total_time_hours = max(0, total_time.total_seconds() / 3600)
        
        # Calculate time risk using the formula
        epsilon = 1
        if time_left_hours <= 0:
            # Task is overdue - calculate how much time is needed vs how much is overdue
            overdue_hours = abs(time_left_hours)
            time_risk_percentage = (allocated_hours / (overdue_hours + epsilon)) * 100
        else:
            # Allow risk to exceed 100% to show true severity
            time_risk_percentage = (allocated_hours / (time_left_hours + epsilon)) * 100
        
        # Optional: Calculate urgency ratio including time passed
        urgency_ratio = 0
        if total_time_hours > 0:
            urgency_ratio = (time_passed_hours + allocated_hours) / (total_time_hours + 1)
            urgency_ratio = min(1.0, urgency_ratio)  # Cap at 1.0
        
        # Apply risk boosts for critical time situations
        risk_boosts = []
        final_risk = time_risk_percentage
        
        if time_left_hours < 4:  # Less than 4 hours left
            final_risk += 10
            risk_boosts.append("Very close to deadline (< 4 hours)")
        
        if time_left_hours < allocated_hours / 2:  # Barely enough time left
            final_risk += 10
            risk_boosts.append("Insufficient time remaining")
        
        # Determine risk level based on uncapped risk
        if final_risk >= 200:
            risk_level = "extreme"
        elif final_risk >= 150:
            risk_level = "critical"
        elif final_risk >= 100:
            risk_level = "high"
        elif final_risk >= 60:
            risk_level = "medium"
        elif final_risk >= 30:
            risk_level = "low"
        else:
            risk_level = "minimal"
        
        # Calculate dynamic cache expiration based on time urgency
        def calculate_cache_expiration(time_left_hours):
            if time_left_hours <= 2:
                return 1800  # 30 minutes - extreme urgency
            elif time_left_hours <= 6:
                return 3600  # 1 hour - critical urgency
            elif time_left_hours <= 12:
                return 7200  # 2 hours - high urgency
            elif time_left_hours <= 24:
                return 10800  # 3 hours - moderate urgency
            else:
                return 18000  # 5 hours - low urgency
        
        cache_expiration = calculate_cache_expiration(time_left_hours)
        
        # Prepare result
        result = {
            "task_id": task_id,
            "task_name": task.name,
            "calculation_timestamp": now.isoformat(),
            "time_risk_percentage": round(final_risk, 2),
            "risk_level": risk_level,
            "time_data": {
                "allocated_hours": allocated_hours,
                "time_left_hours": round(time_left_hours, 2),
                "time_passed_hours": round(time_passed_hours, 2),
                "total_time_hours": round(total_time_hours, 2),
                "is_overdue": is_overdue,
                "overdue_hours": round(overdue_hours, 2) if is_overdue else 0,
                "deadline": deadline.isoformat() if deadline else None,
                "start_date": start_date.isoformat() if start_date else None
            },
            "urgency_ratio": round(urgency_ratio, 3),
            "risk_boosts": risk_boosts,
            "formula_used": "Risk (%) = (T_alloc / (T_left + ε)) * 100 (uncapped to show true severity)",
            "cache_info": {
                "expiration_seconds": cache_expiration,
                "next_update": (now + timedelta(seconds=cache_expiration)).isoformat(),
                "update_frequency": f"Every {cache_expiration//3600}h {cache_expiration%3600//60}m" if cache_expiration >= 3600 else f"Every {cache_expiration//60}m"
            },
            "calculation_details": {
                "epsilon": epsilon,
                "base_risk": round(time_risk_percentage, 2),
                "final_risk_with_boosts": round(final_risk, 2),
                "risk_interpretation": {
                    "200%+": "Extreme - Task needs 2x+ more time than available",
                    "150%+": "Critical - Task needs 1.5x+ more time than available", 
                    "100%+": "High - Task needs more time than available",
                    "60-99%": "Medium - Significant time pressure",
                    "30-59%": "Low - Moderate time pressure",
                    "<30%": "Minimal - Adequate time available"
                }
            }
        }
        
        # Store in Redis with dynamic expiration
        try:
            redis_client = get_redis_client()
            cache_key = f"task_time_risk:{task_id}"
            redis_client.setex(cache_key, cache_expiration, result)
        except Exception as e:
            logger.warning(f"Could not cache time risk result for task {task_id}: {str(e)}")
            result["cache_warning"] = f"Could not cache result: {str(e)}"
        
        return {
            "success": True,
            "task_id": task_id,
            "result": result,
            "status": "completed"
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error calculating time risk for task {task_id}: {str(e)}")
        return {"success": False, "message": str(e)}
    finally:
        db.close() 