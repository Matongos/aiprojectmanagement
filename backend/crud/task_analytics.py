from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta
from models.task import Task
from schemas.task import TaskState

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
            Task.state == TaskState.DONE
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
            Task.state, 
            func.count(Task.id).label("count")
        ).filter(
            Task.project_id == project_id
        ).group_by(
            Task.state
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
            Task.state == TaskState.DONE,
            Task.end_date >= start_date
        ).all()
        
        completed_count = len(completed_tasks)
        
        # Calculate average completion time for tasks with start and end dates
        completion_times = []
        for task in completed_tasks:
            if task.start_date and task.end_date:
                time_diff = task.end_date - task.start_date
                completion_times.append(time_diff.total_seconds() / 3600)  # hours
        
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        
        # Tasks that went over budget
        over_budget_tasks = sum(1 for task in completed_tasks 
                               if task.planned_hours and task.progress 
                               and (task.progress / 100.0) * task.planned_hours > task.planned_hours)
        
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

    @staticmethod
    def get_task_analytics_summary(db: Session, current_user_id: int) -> Dict[str, Any]:
        """Get overall task analytics summary."""
        try:
            # Get total tasks for the current user (either created by or assigned to)
            total_tasks = db.query(Task).filter(
                or_(
                    Task.created_by == current_user_id,
                    Task.assigned_to == current_user_id
                )
            ).count()
            
            # Get tasks by status
            tasks_by_status = db.query(
                Task.state,
                func.count(Task.id).label('count')
            ).filter(
                or_(
                    Task.created_by == current_user_id,
                    Task.assigned_to == current_user_id
                )
            ).group_by(Task.state).all()
            
            # Get overdue tasks
            overdue_tasks = db.query(Task).filter(
                and_(
                    or_(
                        Task.created_by == current_user_id,
                        Task.assigned_to == current_user_id
                    ),
                    Task.deadline < func.now(),
                    Task.state != TaskState.DONE
                )
            ).count()
            
            # Get average completion time
            completed_tasks = db.query(Task).filter(
                and_(
                    or_(
                        Task.created_by == current_user_id,
                        Task.assigned_to == current_user_id
                    ),
                    Task.state == TaskState.DONE,
                    Task.start_date.isnot(None),
                    Task.end_date.isnot(None)
                )
            ).all()
            
            completion_times = []
            for task in completed_tasks:
                time_diff = task.end_date - task.start_date
                completion_times.append(time_diff.total_seconds() / 3600)  # hours
            
            avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
            
            return {
                'total_tasks': total_tasks,
                'tasks_by_status': {
                    str(status): count for status, count in tasks_by_status
                },
                'overdue_tasks': overdue_tasks,
                'overdue_percentage': round((overdue_tasks / total_tasks * 100), 2) if total_tasks > 0 else 0,
                'avg_completion_time_hours': round(avg_completion_time, 2)
            }
            
        except Exception as e:
            print(f"Error getting task analytics summary: {str(e)}")
            return {
                'total_tasks': 0,
                'tasks_by_status': {},
                'overdue_tasks': 0,
                'overdue_percentage': 0,
                'avg_completion_time_hours': 0
            }

    @staticmethod
    def get_task_trend_data(db: Session, days: int = 30) -> List[Dict[str, Any]]:
        """Get task creation and completion trend data for the specified number of days."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get daily task creation counts
            created_tasks = db.query(
                func.date(Task.created_at).label('date'),
                func.count(Task.id).label('count')
            ).filter(
                Task.created_at >= start_date
            ).group_by(
                func.date(Task.created_at)
            ).all()
            
            # Get daily task completion counts
            completed_tasks = db.query(
                func.date(Task.end_date).label('date'),
                func.count(Task.id).label('count')
            ).filter(
                and_(
                    Task.end_date >= start_date,
                    Task.state == TaskState.DONE
                )
            ).group_by(
                func.date(Task.end_date)
            ).all()
            
            # Create a dictionary for easy lookup
            trend_data = {}
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.date().isoformat()
                trend_data[date_str] = {
                    'date': date_str,
                    'created': 0,
                    'completed': 0
                }
                current_date += timedelta(days=1)
            
            # Fill in actual counts
            for date, count in created_tasks:
                date_str = date.isoformat()
                if date_str in trend_data:
                    trend_data[date_str]['created'] = count
            
            for date, count in completed_tasks:
                date_str = date.isoformat()
                if date_str in trend_data:
                    trend_data[date_str]['completed'] = count
            
            return list(trend_data.values())
            
        except Exception as e:
            print(f"Error getting task trend data: {str(e)}")
            return []

task_analytics = TaskAnalytics() 