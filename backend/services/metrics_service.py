from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from models.task import Task
from models.activity import Activity

class MetricsService:
    @staticmethod
    def calculate_productivity_score(db: Session, user_id: int, days: int = 30) -> float:
        """
        Calculate productivity score based on multiple factors:
        - Task completion rate
        - On-time delivery rate
        - Average task completion time
        - Task complexity
        - Quality of work
        
        Returns a score between 0 and 1
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get tasks for the period
        tasks = db.query(Task).filter(
            Task.created_at >= start_date,
            Task.created_at <= end_date,
            Task.assigned_to == user_id
        ).all()
        
        if not tasks:
            return 0.0
            
        # Calculate completion rate (25% weight)
        completed_tasks = sum(1 for task in tasks if task.state == 'COMPLETED')
        completion_rate = completed_tasks / len(tasks)
        
        # Calculate on-time delivery rate (25% weight)
        on_time_tasks = sum(1 for task in tasks 
            if task.state == 'COMPLETED' 
            and task.deadline 
            and task.updated_at <= task.deadline)
        on_time_rate = on_time_tasks / len(tasks) if tasks else 0
        
        # Calculate average completion time score (20% weight)
        completion_times = []
        for task in tasks:
            if task.state == 'COMPLETED' and task.created_at and task.updated_at:
                duration = (task.updated_at - task.created_at).total_seconds() / 3600  # hours
                completion_times.append(duration)
        
        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
        # Convert to a score (lower is better, max 72 hours)
        time_score = max(0, 1 - (avg_completion_time / 72))
        
        # Calculate task complexity score (15% weight)
        complexity_score = 0.0
        for task in tasks:
            # Base complexity on number of activities, comments, and subtasks
            activities_count = db.query(Activity).filter(Activity.task_id == task.id).count()
            complexity = min(1.0, activities_count / 20)  # Cap at 20 activities
            complexity_score += complexity
        complexity_score = complexity_score / len(tasks) if tasks else 0
        
        # Calculate quality score (15% weight)
        quality_score = 0.0
        for task in tasks:
            if task.state == 'COMPLETED':
                # Count revisions (status changes back to IN_PROGRESS)
                revisions = db.query(Activity).filter(
                    Activity.task_id == task.id,
                    Activity.activity_type == 'task_update',
                    Activity.description.like('%status%IN_PROGRESS%')
                ).count()
                task_quality = max(0, 1 - (revisions * 0.2))  # Each revision reduces score by 20%
                quality_score += task_quality
        quality_score = quality_score / completed_tasks if completed_tasks > 0 else 0
        
        # Calculate final weighted score
        productivity_score = (
            (completion_rate * 0.25) +          # 25% weight
            (on_time_rate * 0.25) +            # 25% weight
            (time_score * 0.20) +              # 20% weight
            (complexity_score * 0.15) +        # 15% weight
            (quality_score * 0.15)             # 15% weight
        )
        
        return round(productivity_score, 2)

    @staticmethod
    def calculate_average_completion_time(db: Session, user_id: int, days: int = 30) -> Dict:
        """
        Calculate average completion time with AI insights.
        Returns both the average time and AI-based insights.
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get completed tasks for the period
        tasks = db.query(Task).filter(
            Task.created_at >= start_date,
            Task.created_at <= end_date,
            Task.assigned_to == user_id,
            Task.state == 'COMPLETED'
        ).all()
        
        if not tasks:
            return {
                "average_hours": 0,
                "trend": 0,
                "insights": "No completed tasks in the selected period"
            }
        
        # Calculate completion times
        completion_times = []
        for task in tasks:
            if task.created_at and task.updated_at:
                duration = (task.updated_at - task.created_at).total_seconds() / 3600  # hours
                completion_times.append(duration)
        
        if not completion_times:
            return {
                "average_hours": 0,
                "trend": 0,
                "insights": "No valid completion times found"
            }
        
        # Calculate average and trend
        average_time = sum(completion_times) / len(completion_times)
        
        # Calculate trend (comparing with previous period)
        previous_start = start_date - timedelta(days=days)
        previous_tasks = db.query(Task).filter(
            Task.created_at >= previous_start,
            Task.created_at < start_date,
            Task.assigned_to == user_id,
            Task.state == 'COMPLETED'
        ).all()
        
        previous_times = []
        for task in previous_tasks:
            if task.created_at and task.updated_at:
                duration = (task.updated_at - task.created_at).total_seconds() / 3600
                previous_times.append(duration)
        
        previous_average = sum(previous_times) / len(previous_times) if previous_times else average_time
        trend_percentage = ((average_time - previous_average) / previous_average * 100) if previous_average > 0 else 0
        
        # AI-based insights
        insights = []
        if completion_times:
            # Analyze patterns
            if trend_percentage < -10:
                insights.append("Your completion speed has improved significantly")
            elif trend_percentage > 10:
                insights.append("Tasks are taking longer than usual")
            
            # Check for consistency
            time_std_dev = (sum((t - average_time) ** 2 for t in completion_times) / len(completion_times)) ** 0.5
            if time_std_dev > average_time * 0.5:
                insights.append("High variation in completion times - consider standardizing processes")
            
            # Analyze time of day patterns
            # (This could be enhanced with machine learning for pattern recognition)
            
        return {
            "average_hours": round(average_time, 1),
            "trend": round(trend_percentage, 1),
            "insights": insights if insights else ["Completion times are within normal range"]
        } 