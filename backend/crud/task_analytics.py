from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta
from models.task import Task
from crud.task import task

class TaskAnalytics:
    @staticmethod
    def calculate_project_completion_rate(
        db: Session, *, project_id: int
    ) -> Dict[str, Any]:
        """
        Calculate the completion rate of tasks in a project.
        Returns a dictionary with total tasks count, completed tasks count, and completion rate.
        """
        total_count = db.query(Task).filter(Task.project_id == project_id).count()
        
        if total_count == 0:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "completion_rate": 0.0
            }
            
        completed_count = db.query(Task).filter(
            Task.project_id == project_id,
            Task.status == "done"
        ).count()
        
        completion_rate = (completed_count / total_count) * 100.0
        
        return {
            "total_tasks": total_count,
            "completed_tasks": completed_count,
            "completion_rate": round(completion_rate, 2)
        }
    
    @staticmethod
    def get_task_distribution_by_status(
        db: Session, *, project_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get the distribution of tasks by status for a project.
        Returns a list of dictionaries with status and count.
        """
        result = db.query(
            Task.status, 
            func.count(Task.id).label("count")
        ).filter(
            Task.project_id == project_id
        ).group_by(
            Task.status
        ).all()
        
        return [{"status": status, "count": count} for status, count in result]
    
    @staticmethod
    def get_user_productivity(
        db: Session, *, user_id: int, days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate user productivity metrics based on completed tasks.
        Returns a dictionary with tasks completed, avg time to complete, and other metrics.
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Tasks completed in the period
        completed_tasks = db.query(Task).filter(
            Task.assigned_to == user_id,
            Task.status == "done",
            Task.completed_at >= start_date
        ).all()
        
        completed_count = len(completed_tasks)
        
        # Calculate average completion time for tasks with start and completion dates
        completion_times = []
        for task in completed_tasks:
            if task.start_date and task.completed_at:
                time_diff = task.completed_at - task.start_date
                completion_times.append(time_diff.total_seconds() / 3600)  # hours
        
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        
        # Tasks that went over budget
        over_budget_tasks = sum(1 for task in completed_tasks 
                               if task.estimated_hours and task.actual_hours 
                               and task.actual_hours > task.estimated_hours)
        
        return {
            "completed_tasks": completed_count,
            "avg_completion_time_hours": round(avg_completion_time, 2),
            "over_budget_tasks": over_budget_tasks,
            "over_budget_percentage": round((over_budget_tasks / completed_count) * 100, 2) if completed_count else 0,
            "days_analyzed": days
        }

    @staticmethod
    def get_user_task_stats(db: Session, user_id: int) -> Dict[str, Any]:
        """Get task statistics for a specific user."""
        try:
            # Get total tasks where user is either creator or assignee
            total_tasks = db.query(Task).filter(
                or_(
                    Task.created_by == user_id,
                    Task.assigned_to == user_id
                )
            ).count()
            
            # Get tasks by status
            tasks_by_status = db.query(
                Task.state,
                func.count(Task.id).label('count')
            ).filter(
                or_(
                    Task.created_by == user_id,
                    Task.assigned_to == user_id
                )
            ).group_by(Task.state).all()
            
            # Get tasks by priority
            tasks_by_priority = db.query(
                Task.priority,
                func.count(Task.id).label('count')
            ).filter(
                or_(
                    Task.created_by == user_id,
                    Task.assigned_to == user_id
                )
            ).group_by(Task.priority).all()
            
            # Get overdue tasks
            overdue_tasks = db.query(Task).filter(
                and_(
                    or_(
                        Task.created_by == user_id,
                        Task.assigned_to == user_id
                    ),
                    Task.deadline < func.now(),
                    Task.state != TaskState.DONE
                )
            ).count()
            
            # Format results
            return {
                'total_tasks': total_tasks,
                'tasks_by_status': {
                    status: count for status, count in tasks_by_status
                },
                'tasks_by_priority': {
                    priority: count for priority, count in tasks_by_priority
                },
                'overdue_tasks': overdue_tasks
            }
            
        except Exception as e:
            print(f"Error getting user task stats: {str(e)}")
            return {
                'total_tasks': 0,
                'tasks_by_status': {},
                'tasks_by_priority': {},
                'overdue_tasks': 0
            }

task_analytics = TaskAnalytics() 