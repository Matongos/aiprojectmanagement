from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from models.task import Task, TaskState
from models.activity import Activity
from models.time_entry import TimeEntry
from services.complexity_service import ComplexityService

class MetricsService:
    @staticmethod
    async def calculate_productivity_score(db: Session, user_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Calculate productivity score using the formula:
        productivity_score = (Σ (task_complexity × 1)) / total_time_spent

        Returns a dictionary containing:
        - overall_score: The final productivity score
        - completed_tasks: Number of completed tasks
        - total_time_spent: Total time spent on tasks (hours)
        - avg_complexity: Average task complexity
        - task_breakdown: List of task details with their scores
        """
        try:
            # Initialize complexity service
            complexity_service = ComplexityService()
            
            # Get completed tasks for the period
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Debug: Print the date range we're searching
            print(f"Searching for tasks between {start_date} and {end_date}")
            print(f"Looking for tasks assigned to user {user_id}")
            
            # Query completed tasks with more flexible conditions
            completed_tasks = db.query(Task).filter(
                Task.assigned_to == user_id,
                Task.state == 'done'  # Use lowercase 'done' as per TaskState enum
            ).all()
            
            # Debug: Print found tasks
            print(f"Found {len(completed_tasks)} completed tasks")
            for task in completed_tasks:
                print(f"Task ID: {task.id}, Name: {task.name}, State: {task.state}")
                print(f"Start Date: {task.start_date}, End Date: {task.end_date}")

            if not completed_tasks:
                print("No completed tasks found, returning zero metrics")
                return {
                    "overall_score": 0.0,
                    "completed_tasks": 0,
                    "total_time_spent": 0,
                    "avg_complexity": 0,
                    "task_breakdown": []
                }

            task_scores = []
            total_time_spent = 0
            
            # Calculate scores for each task
            for task in completed_tasks:
                # Get task complexity
                try:
                    complexity_analysis = await complexity_service.analyze_task_complexity(db, task.id)
                    complexity_score = complexity_analysis.total_score / 100  # Normalize to 0-1
                    print(f"Task {task.id} complexity score: {complexity_score}")
                except Exception as e:
                    print(f"Error getting complexity for task {task.id}: {str(e)}")
                    complexity_score = 0.5  # Default to medium complexity

                # Calculate time spent (in hours)
                time_spent = 0
                if task.start_date and task.end_date:
                    # Calculate total hours between start and end dates
                    time_spent = (task.end_date - task.start_date).total_seconds() / 3600
                    print(f"Task {task.id} time spent from dates: {time_spent} hours")
                else:
                    # If no start/end dates, sum up time entries
                    time_entries = db.query(TimeEntry).filter(
                        TimeEntry.task_id == task.id
                    ).all()
                    time_spent = sum(entry.duration for entry in time_entries) if time_entries else (task.planned_hours or 8)
                    print(f"Task {task.id} time spent from entries: {time_spent} hours")

                total_time_spent += time_spent

                # Calculate individual task score (complexity × 1.0 for quality)
                task_score = complexity_score * 1.0  # Assuming base quality of 1.0
                print(f"Task {task.id} final score: {task_score}")
                
                task_scores.append({
                    "task_id": task.id,
                    "name": task.name,
                    "complexity_score": complexity_score,
                    "time_spent": time_spent,
                    "task_score": task_score
                })

            # Calculate final productivity score
            if total_time_spent > 0:
                overall_score = sum(score["task_score"] for score in task_scores) / total_time_spent
                print(f"Final overall score: {overall_score}")
            else:
                overall_score = 0
                print("Total time spent is 0, setting overall score to 0")

            # Calculate average complexity
            avg_complexity = sum(score["complexity_score"] for score in task_scores) / len(task_scores) if task_scores else 0
            print(f"Average complexity: {avg_complexity}")

            return {
                "overall_score": round(overall_score, 2),
                "completed_tasks": len(completed_tasks),
                "total_time_spent": round(total_time_spent, 2),
                "avg_complexity": round(avg_complexity, 2),
                "task_breakdown": task_scores
            }

        except Exception as e:
            print(f"Error calculating productivity score: {str(e)}")
            raise

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