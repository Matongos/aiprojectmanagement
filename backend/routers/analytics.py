from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, extract, text
from datetime import datetime, timedelta, timezone, date
from pydantic import BaseModel
from sqlalchemy import or_, and_
import json
import logging

from database import get_db
from routers.auth import get_current_user
from schemas.user import User
from crud.task_analytics import TaskAnalytics
from models.task import Task
from models.activity import Activity
from models import TimeEntry
from models.project import Project
from models.ml_models import SuccessPattern, MLModel, HistoricalPattern
from schemas.task import TaskState
from services.ml_service import get_ml_service
from .ai import get_ollama_client
from services.analytics_service import AnalyticsService
from services.metrics_service import MetricsService
from models.user_metrics import UserProductivityMetrics, UserProductivityHistory
from tasks.productivity_updater import update_user_productivity
from services.complexity_service import ComplexityService
from models.task_stage import TaskStage
from services.redis_service import get_redis_client
from tasks.project_progress import calculate_project_progress_task
from celery.result import AsyncResult
from crud.task_risk import TaskRiskCRUD
from models.task_risk import TaskRisk
from models.project import Project, ProjectMember, ProjectRole
from services.ai_service import get_ollama_client

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(get_current_user)],
    responses={404: {"description": "Not found"}},
)

task_analytics = TaskAnalytics()

class TaskTrendItem(BaseModel):
    date: str
    count: int

class TaskTrendResponse(BaseModel):
    created_tasks: List[TaskTrendItem]
    completed_tasks: List[TaskTrendItem]

class CompletionTimeMetrics(BaseModel):
    averageCompletionTime: float
    last7DaysAverage: float
    last30DaysAverage: float
    trend: float
    period: str
    insights: List[str]
    tasksNeedingAttention: int
    tasksOverEstimate: int
    tasksNearDeadline: int
    criticalInsights: List[str]
    warningInsights: List[str]

# Add new schema for dependency analysis
class DependencyExplanation(BaseModel):
    task_name: str
    score: int
    reason: str

class DependencyAnalysis(BaseModel):
    final_score: float
    explanations: List[DependencyExplanation]

@router.get("/dashboard/completion-rate", response_model=Dict[str, Any])
async def get_dashboard_completion_rate(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get completion rate for dashboard based on user role"""
    try:
        # Base query for tasks
        query = db.query(
            func.count(Task.id).label('total_tasks'),
            func.sum(case((Task.state == TaskState.DONE, 1), else_=0)).label('completed_tasks')
        )

        # Apply filters based on user role
        if not current_user.get("is_superuser"):
            # Regular users only see their assigned tasks
            query = query.filter(Task.assigned_to == current_user["id"])
        
        # Execute query
        metrics = query.first()

        total_tasks = metrics.total_tasks or 0
        completed_tasks = metrics.completed_tasks or 0
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        return {
            "completion_rate": round(completion_rate, 2),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "is_superuser_view": current_user.get("is_superuser", False)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/project/{project_id}/completion", response_model=Dict[str, Any])
async def get_project_completion_rate(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get project completion rate statistics"""
    try:
        # Verify project exists and user has access
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # For non-superusers, verify project access
        if not current_user.get("is_superuser"):
            has_access = db.query(Project).join(
                Project.members
            ).filter(
                Project.id == project_id,
                Project.members.any(user_id=current_user["id"])
            ).first() is not None
            
            if not has_access:
                raise HTTPException(status_code=403, detail="No access to this project")

        # Get task metrics for the project
        metrics = db.query(
            func.count(Task.id).label('total_tasks'),
            func.sum(case((Task.state == TaskState.DONE, 1), else_=0)).label('completed_tasks')
        ).filter(Task.project_id == project_id).first()

        total_tasks = metrics.total_tasks or 0
        completed_tasks = metrics.completed_tasks or 0
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Get additional project metrics
        tasks_by_state = db.query(
            Task.state,
            func.count(Task.id).label('count')
        ).filter(
            Task.project_id == project_id
        ).group_by(Task.state).all()

        state_distribution = {state: count for state, count in tasks_by_state}

        return {
            "completion_rate": round(completion_rate, 2),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "tasks_by_state": state_distribution,
            "project_name": project.name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/project/{project_id}/task-distribution", response_model=Dict[str, Any])
async def get_project_task_distribution(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get task distribution by status and priority"""
    try:
        # Get task distribution by state
        status_distribution = db.query(
            Task.state,
            func.count(Task.id).label('count')
        ).filter(
            Task.project_id == project_id
        ).group_by(Task.state).all()

        # Get task distribution by priority
        priority_distribution = db.query(
            Task.priority,
            func.count(Task.id).label('count')
        ).filter(
            Task.project_id == project_id
        ).group_by(Task.priority).all()

        return {
            "status_distribution": {status: count for status, count in status_distribution},
            "priority_distribution": {priority: count for priority, count in priority_distribution}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user/productivity")
async def get_user_productivity(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get current user's productivity metrics using the comprehensive metrics system.
    """
    try:
        # Reuse the specific user productivity logic
        return await get_specific_user_productivity(
            user_id=current_user["id"],
            db=db,
            current_user=current_user
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/user/{user_id}/productivity", response_model=Dict[str, Any])
async def get_specific_user_productivity(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get specific user's productivity metrics using cached data and background updates.
    
    Returns detailed productivity metrics including:
    - Overall productivity score
    - Task completion statistics
    - Average task complexity
    - Time utilization
    - Detailed task breakdown
    """
    try:
        # Check if we have recent cached metrics
        cached_metrics = db.query(UserProductivityMetrics).filter(
            UserProductivityMetrics.user_id == user_id
        ).first()
        
        # If we have recent metrics (less than 6 hours old), use them
        if cached_metrics and cached_metrics.last_updated > datetime.now(cached_metrics.last_updated.tzinfo) - timedelta(hours=6):
            return cached_metrics.to_dict()
            
        # If no cached metrics or they're old, trigger a background update
        update_user_productivity.delay(user_id)
        
        # If we have old cached metrics, return them while the update runs
        if cached_metrics:
            return cached_metrics.to_dict()
            
        # If no cached metrics at all, calculate them synchronously this one time
        metrics_service = MetricsService()
        productivity_metrics = await metrics_service.calculate_productivity_score(db, user_id)
        
        # Store the metrics
        new_metrics = UserProductivityMetrics(
            user_id=user_id,
            productivity_score=productivity_metrics["overall_score"],
            completed_tasks=productivity_metrics["completed_tasks"],
            total_time_spent=productivity_metrics["total_time_spent"],
            avg_complexity=productivity_metrics["avg_complexity"],
            task_breakdown=productivity_metrics["task_breakdown"]
        )
        db.add(new_metrics)
        db.commit()
        
        return new_metrics.to_dict()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/summary")
async def get_task_summary(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get task summary including counts and completion rate"""
    try:
        print(f"\nGetting task summary for user {current_user['id']}")
        print(f"Is superuser: {current_user.get('is_superuser', False)}")
        print(f"Project ID filter: {project_id}")

        # Base query for all tasks
        query = db.query(Task)

        # Apply filters based on user role
        if not current_user.get("is_superuser"):
            # Regular users only see their assigned tasks
            query = query.filter(Task.assigned_to == current_user["id"])
        # Superusers see all tasks, so no additional filter needed

        # If project_id is specified, apply project-specific filters
        if project_id:
            print(f"Filtering for specific project: {project_id}")
            query = query.filter(Task.project_id == project_id)
            
            # Verify project exists
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            
            # For non-superusers, verify project access
            if not current_user.get("is_superuser"):
                has_access = db.query(Project).join(
                    Project.members
                ).filter(
                    Project.id == project_id,
                    Project.members.any(user_id=current_user["id"])
                ).first() is not None
                
                if not has_access:
                    raise HTTPException(status_code=403, detail="No access to this project")

        # Calculate metrics for filtered tasks
        metrics = query.with_entities(
            func.count(Task.id).label('total'),
            func.sum(case((Task.state == TaskState.DONE, 1), else_=0)).label('completed'),
            func.sum(case((Task.state.in_([TaskState.IN_PROGRESS, TaskState.CHANGES_REQUESTED, TaskState.APPROVED]), 1), else_=0)).label('active'),
            func.sum(case((Task.state == TaskState.CANCELED, 1), else_=0)).label('cancelled'),
            func.sum(case((Task.state == TaskState.CHANGES_REQUESTED, 1), else_=0)).label('changes_requested'),
            func.sum(case((Task.state == TaskState.APPROVED, 1), else_=0)).label('approved')
        ).first()

        # Get detailed state breakdown
        states_count = query.with_entities(
            Task.state,
            func.count(Task.id).label('count')
        ).group_by(Task.state).all()

        print("\nTask counts by state:")
        for state, count in states_count:
            print(f"- {state}: {count}")

        # Calculate totals
        total = metrics.total or 0
        completed = metrics.completed or 0
        active = metrics.active or 0
        cancelled = metrics.cancelled or 0
        changes_requested = metrics.changes_requested or 0
        approved = metrics.approved or 0

        # Calculate completion rate
        completion_rate = (completed / total * 100) if total > 0 else 0

        return {
            "total": total,
            "completed": completed,
            "active": active,  # active now includes IN_PROGRESS, CHANGES_REQUESTED, and APPROVED
            "cancelled": cancelled,
            "changes_requested": changes_requested,
            "approved": approved,
            "completion_rate": round(completion_rate, 2),
            "tasks_by_state": {
                "in_progress": active - changes_requested - approved,  # Just IN_PROGRESS tasks
                "completed": completed,
                "cancelled": cancelled,
                "changes_requested": changes_requested,
                "approved": approved
            }
        }
    except Exception as e:
        print(f"Error in get_task_summary: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting task summary: {str(e)}"
        )

@router.get("/tasks/trend", response_model=TaskTrendResponse)
async def get_task_trend(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get task creation and completion trend data"""
    try:
        # Get current time in UTC
        now = datetime.now(timezone.utc)
        # Calculate start date
        start_date = now - timedelta(days=days)
        
        # Get daily task creation counts
        created_tasks_query = db.query(
            func.date_trunc('day', Task.created_at).label('date'),
            func.count(Task.id).label('count')
        ).filter(
            Task.created_at >= start_date,
            Task.created_at <= now
        ).group_by(text('date')).order_by(text('date')).all()

        # Get daily task completion counts
        completed_tasks_query = db.query(
            func.date_trunc('day', Task.updated_at).label('date'),
            func.count(Task.id).label('count')
        ).filter(
            Task.state == TaskState.DONE,
            Task.updated_at >= start_date,
            Task.updated_at <= now
        ).group_by(text('date')).order_by(text('date')).all()

        # Convert to the expected format
        created_tasks = []
        completed_tasks = []

        # Create a dictionary to store counts by date
        created_by_date = {date.date(): count for date, count in created_tasks_query}
        completed_by_date = {date.date(): count for date, count in completed_tasks_query}

        # Generate a list of all dates in the range
        current_date = start_date
        while current_date <= now:
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Get counts for this date (0 if no tasks)
            created_count = created_by_date.get(current_date.date(), 0)
            completed_count = completed_by_date.get(current_date.date(), 0)
            
            created_tasks.append(TaskTrendItem(date=date_str, count=created_count))
            completed_tasks.append(TaskTrendItem(date=date_str, count=completed_count))
            
            current_date += timedelta(days=1)

        print(f"\nTask trend for last {days} days:")
        print(f"Created tasks: {sum(t.count for t in created_tasks)}")
        print(f"Completed tasks: {sum(t.count for t in completed_tasks)}")

        return TaskTrendResponse(
            created_tasks=created_tasks,
            completed_tasks=completed_tasks
        )
    except Exception as e:
        print(f"Error in get_task_trend: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting task trend: {str(e)}"
        )

async def generate_ai_insights(
    tasks_data: dict,
    completion_metrics: dict,
    db: Session
) -> tuple[List[str], List[str], List[str]]:
    """Generate AI-powered insights focusing on implemented metrics"""
    try:
        # Prepare core metrics we already have implemented
        analysis_data = {
            "completion_metrics": {
                "average_time": completion_metrics.get("avg_completion_time", 0),
                "last_7_days": completion_metrics.get("last_7days_avg", 0),
                "last_30_days": completion_metrics.get("last_30days_avg", 0),
                "trend": completion_metrics.get("trend", 0)
            },
            "task_status": {
                "total": tasks_data.get("total", 0),
                "completed": tasks_data.get("completed", 0),
                "active": tasks_data.get("active", 0),
                "needing_attention": completion_metrics.get("tasks_needing_attention", 0),
                "over_estimate": completion_metrics.get("tasks_over_planned", 0),
                "near_deadline": completion_metrics.get("tasks_near_deadline", 0)
            }
        }

        # Prepare focused prompt for initial AI analysis
        prompt = f"""
        Analyze these project metrics and provide specific insights:
        {json.dumps(analysis_data, indent=2)}

        Provide insights in these specific areas:
        1. Task Completion Efficiency (CRITICAL if average time increasing, INSIGHT if decreasing)
        2. Time Estimation Accuracy (CRITICAL if multiple tasks over estimate)
        3. Deadline Risk (WARNING for tasks near deadline)
        4. Task Progress (WARNING for stalled tasks, INSIGHT for good progress)

        Format each insight on a new line starting with CRITICAL:, WARNING:, or INSIGHT:
        Be specific with numbers and comparisons.
        Limit to most important 1-2 insights per category.
        """

        # Get AI client and generate insights
        client = get_ollama_client()
        response = await client.generate(
            model="llama2",
            prompt=prompt,
            max_tokens=300,
            temperature=0.3  # Lower temperature for more focused insights
        )

        # Parse AI response
        critical_insights = []
        warning_insights = []
        positive_insights = []

        if response and response.text:
            lines = response.text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('CRITICAL:'):
                    critical_insights.append(line.replace('CRITICAL:', '').strip())
                elif line.startswith('WARNING:'):
                    warning_insights.append(line.replace('WARNING:', '').strip())
                elif line.startswith('INSIGHT:'):
                    positive_insights.append(line.replace('INSIGHT:', '').strip())

        return critical_insights, warning_insights, positive_insights

    except Exception as e:
        print(f"Error generating AI insights: {str(e)}")
        return [], [], []

@router.get("/tasks/completion-time", response_model=CompletionTimeMetrics)
async def get_completion_time_metrics(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get task completion time metrics and insights"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Get completed tasks for different time periods
        base_query = db.query(Task)
        if not current_user.get("is_superuser"):
            base_query = base_query.filter(Task.assigned_to == current_user["id"])

        completed_tasks_period = base_query.filter(
            Task.state == TaskState.DONE,
            Task.updated_at >= start_date
        ).all()
        
        completed_tasks_7days = base_query.filter(
            Task.state == TaskState.DONE,
            Task.updated_at >= seven_days_ago
        ).all()
        
        completed_tasks_30days = base_query.filter(
            Task.state == TaskState.DONE,
            Task.updated_at >= thirty_days_ago
        ).all()

        # Calculate metrics for each period
        def calculate_period_metrics(tasks):
            completion_times = []
            tasks_over_planned = 0
            
            for task in tasks:
                # Use task's start_date and end_date for completion time calculation
                if task.start_date and task.end_date:
                    # Calculate total hours between start and end (24-hour basis)
                    completion_time = (task.end_date - task.start_date).total_seconds() / 3600
                    completion_times.append(completion_time)
                    
                    if task.planned_hours and completion_time > task.planned_hours:
                        tasks_over_planned += 1
            
            avg_time = sum(completion_times) / len(completion_times) if completion_times else 0
            return avg_time, tasks_over_planned, len(completion_times)

        # Calculate averages for each period
        avg_completion_time, tasks_over_planned, total_tasks = calculate_period_metrics(completed_tasks_period)
        last_7days_avg, _, tasks_7days = calculate_period_metrics(completed_tasks_7days)
        last_30days_avg, _, tasks_30days = calculate_period_metrics(completed_tasks_30days)
        
        # Calculate trend (comparing to previous period)
        previous_start = start_date - timedelta(days=days)
        previous_tasks = db.query(Task).filter(
            Task.state == TaskState.DONE,
            Task.updated_at >= previous_start,
            Task.updated_at < start_date
        ).all()
        
        previous_avg, _, _ = calculate_period_metrics(previous_tasks)
        trend = ((avg_completion_time - previous_avg) / previous_avg) if previous_avg > 0 else 0
        
        # Get tasks needing attention (unchanged for 7 business days)
        attention_query = db.query(func.count(Task.id))
        if not current_user.get("is_superuser"):
            attention_query = attention_query.filter(Task.assigned_to == current_user["id"])
        
        tasks_needing_attention = attention_query.filter(
            Task.state.in_([TaskState.IN_PROGRESS, TaskState.CHANGES_REQUESTED, TaskState.APPROVED]),
            Task.updated_at <= datetime.utcnow() - timedelta(days=7)
        ).scalar()

        # Get tasks near deadline
        deadline_query = db.query(func.count(Task.id))
        if not current_user.get("is_superuser"):
            deadline_query = deadline_query.filter(Task.assigned_to == current_user["id"])
        
        tasks_near_deadline = deadline_query.filter(
            Task.state != TaskState.DONE,
            Task.deadline <= datetime.utcnow() + timedelta(days=3),
            Task.deadline > datetime.utcnow()
        ).scalar()
        
        # Get task summary for AI analysis
        active_query = db.query(func.count(Task.id))
        if not current_user.get("is_superuser"):
            active_query = active_query.filter(Task.assigned_to == current_user["id"])
            
        task_summary = {
            "total": total_tasks,
            "completed": tasks_30days,
            "active": active_query.filter(
                Task.state.in_([TaskState.IN_PROGRESS, TaskState.CHANGES_REQUESTED, TaskState.APPROVED])
            ).scalar(),
            "completion_rate": (tasks_30days / total_tasks * 100) if total_tasks > 0 else 0
        }

        # Prepare metrics for AI analysis
        completion_metrics = {
            "avg_completion_time": avg_completion_time,
            "last_7days_avg": last_7days_avg,
            "last_30days_avg": last_30days_avg,
            "trend": trend,
            "tasks_needing_attention": tasks_needing_attention,
            "tasks_over_planned": tasks_over_planned,
            "tasks_near_deadline": tasks_near_deadline
        }

        # Generate AI insights
        ai_critical, ai_warnings, ai_insights = await generate_ai_insights(
            task_summary,
            completion_metrics,
            db
        )

        # Combine AI insights with calculated metrics
        critical_insights = ai_critical + [
            f"{tasks_needing_attention} tasks have not been updated in over 7 business days"
            if tasks_needing_attention > 0 else None
        ]
        
        warning_insights = ai_warnings + [
            f"{tasks_over_planned} tasks exceeded their planned hours"
            if tasks_over_planned > 0 else None,
            f"{tasks_near_deadline} tasks are approaching their deadlines"
            if tasks_near_deadline > 0 else None
        ]
        
        insights = ai_insights + [
            f"Completed {tasks_7days} tasks in the last 7 days"
            if tasks_7days > 0 else None,
            f"Completed {tasks_30days} tasks in the last 30 days"
            if tasks_30days > 0 else None
        ]

        # Filter out None values
        critical_insights = [i for i in critical_insights if i]
        warning_insights = [i for i in warning_insights if i]
        insights = [i for i in insights if i]
        
        return CompletionTimeMetrics(
            averageCompletionTime=round(avg_completion_time, 2),
            last7DaysAverage=round(last_7days_avg, 2),
            last30DaysAverage=round(last_30days_avg, 2),
            trend=round(trend, 3),
            period=f"{days}d",
            insights=insights,
            tasksNeedingAttention=tasks_needing_attention,
            tasksOverEstimate=tasks_over_planned,
            tasksNearDeadline=tasks_near_deadline,
            criticalInsights=critical_insights,
            warningInsights=warning_insights
        )
    except Exception as e:
        print(f"Error in get_completion_time_metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting completion time metrics: {str(e)}"
        )

@router.get("/tasks/active", response_model=Dict[str, Any])
async def get_active_tasks_count(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get count of active tasks"""
    try:
        # Base query
        query = db.query(func.count(Task.id))

        # Apply filters based on user role
        if not current_user.get("is_superuser"):
            # Regular users only see their assigned tasks
            query = query.filter(Task.assigned_to == current_user["id"])
        
        # Apply active states filter
        active_count = query.filter(
            Task.state.in_([TaskState.IN_PROGRESS, TaskState.CHANGES_REQUESTED, TaskState.APPROVED])
        ).scalar()
    
        return {"active_tasks": active_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tasks/productivity")
async def get_productivity_metrics(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get productivity metrics for tasks"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get completed tasks in period
        completed_tasks = db.query(Task).filter(
            Task.state == TaskState.DONE,
            Task.updated_at >= start_date,
            Task.start_date.isnot(None),  # Ensure we have start date
            Task.end_date.isnot(None)     # Ensure we have end date
        ).all()
        
        # Calculate metrics
        total_completed = len(completed_tasks)
        
        # Calculate total time based on start and end dates
        total_time = sum(
            (task.end_date - task.start_date).total_seconds() / 3600  # Convert to hours
            for task in completed_tasks
        )
        
        avg_time_per_task = total_time / total_completed if total_completed > 0 else 0

        return {
            "completed_tasks": total_completed,
            "total_time_spent": round(total_time, 2),
            "average_time_per_task": round(avg_time_per_task, 2)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting productivity metrics: {str(e)}"
        )

@router.get("/ml/task/{task_id}/predict-completion", response_model=Dict[str, Any])
async def predict_task_completion(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Predict task completion time using ML model"""
    try:
        ml_service = get_ml_service(db)
        return await ml_service.predict_task_completion_time(task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ml/success-patterns", response_model=Dict[str, Any])
async def get_success_patterns(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get identified success patterns across projects"""
    try:
        patterns = db.query(SuccessPattern).order_by(
            SuccessPattern.impact_score.desc()
        ).all()
        
        return {
            "patterns": [
                {
                    "type": p.pattern_type,
                    "data": p.pattern_data,
                    "confidence": p.confidence_score,
                    "impact": p.impact_score,
                    "occurrences": p.occurrence_count
                }
                for p in patterns
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ml/models/performance", response_model=Dict[str, Any])
async def get_ml_model_performance(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get performance metrics for active ML models"""
    try:
        models = db.query(MLModel).filter(
            MLModel.is_active == True
        ).order_by(MLModel.last_trained.desc()).all()
        
        return {
            "models": [
                {
                    "name": m.model_name,
                    "type": m.model_type,
                    "version": m.model_version,
                    "performance": m.performance_metrics,
                    "feature_importance": m.feature_importance,
                    "last_trained": m.last_trained.isoformat() if m.last_trained else None
                }
                for m in models
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/projects/{project_id}/average-completion-time")
async def get_project_average_completion_time(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """
    Calculate the average completion time for tasks in a project.
    Returns both the raw average in seconds and a human-readable format.
    Uses 24-hour time calculation (all hours count).
    """
    try:
        # Get all completed tasks in the project with valid start and end dates
        completed_tasks = db.query(Task).filter(
            Task.project_id == project_id,
            Task.state == TaskState.DONE,
            Task.start_date.isnot(None),
            Task.end_date.isnot(None)
        ).all()
        
        if not completed_tasks:
            return {
                "average_completion_time_seconds": 0,
                "average_completion_time_human": "No completed tasks found",
                "total_tasks_analyzed": 0
            }
        
        # Calculate completion time for each task (in seconds)
        completion_times = [
            (task.end_date - task.start_date).total_seconds()
            for task in completed_tasks
        ]
        
        # Calculate average
        avg_seconds = sum(completion_times) / len(completion_times)
        
        # Convert to human-readable format
        avg_hours = avg_seconds / 3600
        
        return {
            "average_completion_time_seconds": avg_seconds,
            "average_completion_time_human": f"{round(avg_hours, 2)} hours",
            "total_tasks_analyzed": len(completed_tasks)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating average completion time: {str(e)}"
        )

@router.get("/user/productivity/all")
async def get_all_users_productivity(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get productivity metrics for all users.
    Only accessible by superusers/admins.
    """
    try:
        # Check if user is superuser/admin
        if not current_user.get("is_superuser"):
            raise HTTPException(
                status_code=403,
                detail="Only administrators can view all users' productivity metrics"
            )
            
        # Get all cached metrics
        metrics = db.query(UserProductivityMetrics).all()
        
        # If we have no metrics at all, trigger background updates
        if not metrics:
            from tasks.productivity_updater import update_all_users_productivity
            update_all_users_productivity.delay()
            return {
                "message": "No metrics available yet. Updates have been triggered.",
                "metrics": []
            }
            
        # Convert metrics to response format
        users_metrics = []
        for metric in metrics:
            # Skip metrics older than 6 hours and trigger an update
            if metric.last_updated < datetime.now(metric.last_updated.tzinfo) - timedelta(hours=6):
                from tasks.productivity_updater import update_user_productivity
                update_user_productivity.delay(metric.user_id)
            
            # Include metrics in response
            users_metrics.append({
                "user_id": metric.user_id,
                "metrics": metric.to_dict(),
                "last_updated": metric.last_updated.isoformat()
            })
            
        return {
            "metrics": users_metrics,
            "total_users": len(users_metrics)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/tasks/global-completion-metrics")
async def get_global_completion_metrics(
    days: Optional[int] = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get global completion metrics for all completed tasks.
    Only accessible by superusers and project managers.
    
    Returns:
    - Average completion time
    - Total completed tasks
    - Completion metrics by project
    - Completion metrics by user
    - Task complexity distribution
    """
    try:
        # Check if user is superuser or project manager
        if not (current_user.get("is_superuser") or current_user.get("is_project_manager")):
            raise HTTPException(
                status_code=403,
                detail="Only administrators and project managers can view global completion metrics"
            )
            
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get all completed tasks with valid start and end dates
        completed_tasks = db.query(Task).filter(
            Task.state == TaskState.DONE,
            Task.start_date.isnot(None),
            Task.end_date.isnot(None),
            Task.end_date >= start_date
        ).all()
        
        if not completed_tasks:
            return {
                "message": "No completed tasks found in the specified period",
                "metrics": {
                    "average_completion_time": 0,
                    "total_completed": 0,
                    "by_project": {},
                    "by_user": {},
                    "complexity_distribution": {}
                }
            }
            
        # Calculate global metrics
        total_time = 0
        project_metrics = {}
        user_metrics = {}
        complexity_levels = {"low": 0, "medium": 0, "high": 0}
        
        for task in completed_tasks:
            # Calculate completion time in hours
            completion_time = (task.end_date - task.start_date).total_seconds() / 3600
            total_time += completion_time
            
            # Group by project
            if task.project_id not in project_metrics:
                project_metrics[task.project_id] = {
                    "total_tasks": 0,
                    "total_time": 0,
                    "avg_time": 0,
                    "project_name": task.project.name if task.project else f"Project {task.project_id}"
                }
            project_metrics[task.project_id]["total_tasks"] += 1
            project_metrics[task.project_id]["total_time"] += completion_time
            
            # Group by user
            if task.assigned_to not in user_metrics:
                user_metrics[task.assigned_to] = {
                    "total_tasks": 0,
                    "total_time": 0,
                    "avg_time": 0
                }
            user_metrics[task.assigned_to]["total_tasks"] += 1
            user_metrics[task.assigned_to]["total_time"] += completion_time
            
            # Categorize complexity
            if task.complexity_score is not None:
                if task.complexity_score < 0.4:
                    complexity_levels["low"] += 1
                elif task.complexity_score < 0.7:
                    complexity_levels["medium"] += 1
                else:
                    complexity_levels["high"] += 1
        
        # Calculate averages
        global_avg = total_time / len(completed_tasks)
        
        # Calculate project averages
        for project in project_metrics.values():
            project["avg_time"] = round(project["total_time"] / project["total_tasks"], 2)
            project["total_time"] = round(project["total_time"], 2)
            
        # Calculate user averages
        for user in user_metrics.values():
            user["avg_time"] = round(user["total_time"] / user["total_tasks"], 2)
            user["total_time"] = round(user["total_time"], 2)
            
        return {
            "metrics": {
                "average_completion_time": round(global_avg, 2),
                "total_completed": len(completed_tasks),
                "by_project": project_metrics,
                "by_user": user_metrics,
                "complexity_distribution": complexity_levels
            },
            "period_days": days
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/projects/{project_id}/progress")
async def queue_project_progress_calculation(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    celery_task = calculate_project_progress_task.delay(project_id)
    return {
        "status": "queued",
        "project_id": project_id,
        "celery_task_id": celery_task.id
    }

@router.get("/projects/{project_id}/progress/status/{celery_task_id}")
async def get_project_progress_status(celery_task_id: str):
    result = AsyncResult(celery_task_id)
    return {
        "task_id": celery_task_id,
        "state": result.state,
        "result": result.result if result.ready() else None
    }

@router.get("/tasks/{task_id}/dependency-analysis", response_model=DependencyAnalysis)
async def analyze_task_dependencies(
    task_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Analyze task dependencies within a specific project.
    Algorithm:
    1. Verify project exists and user has access
    2. Get target task and verify it's in the project
    3. Get all active tasks in the same project
    4. Analyze dependencies using Mistral AI
    """
    try:
        print(f"\n=== Starting Dependency Analysis ===")
        print(f"Analyzing task {task_id} in project {project_id}")

        # 1. First verify project exists and user has access
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            print(f"Project {project_id} not found")
            raise HTTPException(
                status_code=404,
                detail="Project not found"
            )

        print(f"Found project: {project.name}")

        # Check user has access to project if not superuser
        if not current_user.get("is_superuser"):
            has_access = db.query(Project).join(
                Project.members
            ).filter(
                Project.id == project_id,
                Project.members.any(user_id=current_user["id"])
            ).first() is not None
            
            if not has_access:
                print(f"User {current_user['id']} does not have access to project {project_id}")
                raise HTTPException(
                    status_code=403,
                    detail="No access to this project"
                )

        # 2. Get target task and verify it belongs to this project
        target_task = db.query(Task).filter(
            Task.id == task_id,
            Task.project_id == project_id  # Explicitly check project
        ).first()
        
        if not target_task:
            print(f"Task {task_id} not found in project {project_id}")
            raise HTTPException(
                status_code=404, 
                detail=f"Task {task_id} not found in project {project_id}"
            )

        print(f"Found target task: {target_task.name} (State: {target_task.state})")

        # Get ALL tasks in project first (for debugging)
        all_project_tasks = db.query(Task).filter(
            Task.project_id == project_id,
            Task.id != task_id
        ).all()

        print(f"\nAll tasks in project (excluding target):")
        for t in all_project_tasks:
            print(f"- Task {t.id}: {t.name} (State: {t.state})")

        # 3. Get all active tasks in the same project (excluding target task)
        active_tasks = db.query(Task).filter(
            Task.project_id == project_id,  # Filter by project first
            Task.id != task_id,  # Exclude target task
            Task.state.in_(['in_progress', 'approved', 'changes_requested'])
        ).all()

        print(f"\nActive tasks found: {len(active_tasks)}")
        if active_tasks:
            print("Active tasks:")
            for t in active_tasks:
                print(f"- Task {t.id}: {t.name} (State: {t.state})")
        else:
            print("States of all tasks in project:")
            task_states = db.query(Task.state, func.count(Task.id)).filter(
                Task.project_id == project_id
            ).group_by(Task.state).all()
            for state, count in task_states:
                print(f"- {state}: {count} tasks")

            return DependencyAnalysis(
                final_score=0.0,
                explanations=[]
            )

        # 4. Analyze each active task using Mistral
        client = get_ollama_client()
        explanations = []
        total_score = 0

        for task in active_tasks:
            # Prepare AI input
            analysis_input = {
                "target_task": {
                    "name": target_task.name,
                    "description": target_task.description or "",
                    "project": project.name  # Include project context
                },
                "candidate_task": {
                    "name": task.name,
                    "description": task.description or "",
                    "project": project.name  # Include project context
                }
            }

            # Create AI prompt with project context
            prompt = f"""Given the following two tasks in project "{project.name}":

Task under evaluation: "{analysis_input['target_task']['name']}"
Description: "{analysis_input['target_task']['description']}"

Candidate task: "{analysis_input['candidate_task']['name']}"
Description: "{analysis_input['candidate_task']['description']}"

Does the candidate task logically depend on the evaluated task within the context of project "{project.name}"?
Respond in JSON format with three fields:
- depends: true/false
- reasoning: 1-2 sentence explanation
- score: 0-100 (where 0 means not dependent, 100 means strongly dependent)

Example response:
{{
    "depends": true,
    "reasoning": "Task A cannot proceed without Task B's backend logic.",
    "score": 90
}}

Return ONLY valid JSON."""

            # Get AI analysis
            try:
                response = await client.generate(
                    model="mistral",
                    prompt=prompt,
                    max_tokens=200,
                    temperature=0.1
                )
                
                # Parse response
                analysis_text = response.response if hasattr(response, 'response') else str(response)
                analysis = json.loads(analysis_text)

                # Add to results
                score = int(analysis.get('score', 0))
                total_score += score
                
                explanations.append(DependencyExplanation(
                    task_name=task.name,
                    score=score,
                    reason=analysis.get('reasoning', 'No reasoning provided')
                ))

            except Exception as e:
                print(f"Error analyzing task {task.id}: {str(e)}")
                continue

        # 5. Calculate final score
        if explanations:
            # Scale the average score down to 0-10 range
            final_score = round((total_score / len(explanations)) / 10, 2)
        else:
            final_score = 0.0

        # 6. Return results
        return DependencyAnalysis(
            final_score=final_score,
            explanations=sorted(explanations, key=lambda x: x.score, reverse=True)
        )

    except Exception as e:
        print(f"Error in dependency analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing task dependencies: {str(e)}"
        )

@router.get("/user/productivity/trend", response_model=Dict[str, Any])
async def get_user_productivity_trend(
    user_id: int,
    days: int = 30,
    period_type: str = "daily",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get productivity trend for a specific user over a specified period.
    
    Args:
        user_id: ID of the user to get trends for
        days: Number of days to look back (default: 30)
        period_type: Type of period ('daily', 'weekly', 'monthly')
    """
    try:
        # Check if user is superuser or project manager
        if not (current_user.get("is_superuser") or current_user.get("is_project_manager")):
            raise HTTPException(
                status_code=403,
                detail="Only administrators and project managers can view productivity trends"
            )
            
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        # Get productivity history for the user
        history = db.query(UserProductivityHistory).filter(
            UserProductivityHistory.user_id == user_id,
            UserProductivityHistory.period_type == period_type,
            UserProductivityHistory.snapshot_date >= start_date,
            UserProductivityHistory.snapshot_date <= end_date
        ).order_by(UserProductivityHistory.snapshot_date).all()
        
        if not history:
            return {
                "message": "No productivity history found for the specified period",
                "trends": [],
                "summary": {
                    "overall_trend": "stable",
                    "average_score": 0.0,
                    "best_day": None,
                    "worst_day": None,
                    "consistency_score": 0.0
                }
            }
        
        # Extract productivity data from history
        trends = []
        scores = []
        
        for record in history:
            trends.append({
                "date": record.snapshot_date.isoformat(),
                "productivity_score": record.productivity_score,
                "completed_tasks": record.completed_tasks,
                "total_time_spent": record.total_time_spent,
                "avg_complexity": record.avg_complexity,
                "completion_rate": record.completion_rate,
                "avg_completion_time": record.avg_completion_time,
                "trend": record.score_trend,
                "trend_percentage": record.trend_percentage
            })
            scores.append(record.productivity_score)
        
        # Calculate summary statistics
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # Find best and worst days
        best_record = max(history, key=lambda x: x.productivity_score)
        worst_record = min(history, key=lambda x: x.productivity_score)
        
        # Calculate consistency (standard deviation)
        if len(scores) > 1:
            mean_score = sum(scores) / len(scores)
            variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
            std_dev = variance ** 0.5
            consistency_score = max(0, 100 - (std_dev / mean_score * 100)) if mean_score > 0 else 0
        else:
            consistency_score = 100.0
        
        # Determine overall trend
        if len(history) >= 2:
            first_score = history[0].productivity_score
            last_score = history[-1].productivity_score
            if last_score > first_score * 1.1:
                overall_trend = "up"
            elif last_score < first_score * 0.9:
                overall_trend = "down"
            else:
                overall_trend = "stable"
        else:
            overall_trend = "stable"
        
        return {
            "trends": trends,
            "summary": {
                "overall_trend": overall_trend,
                "average_score": round(avg_score, 2),
                "best_day": {
                    "date": best_record.snapshot_date.isoformat(),
                    "score": best_record.productivity_score
                },
                "worst_day": {
                    "date": worst_record.snapshot_date.isoformat(),
                    "score": worst_record.productivity_score
                },
                "consistency_score": round(consistency_score, 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting productivity trend: {str(e)}"
        )

@router.post("/user/productivity/snapshot", response_model=Dict[str, Any])
async def create_user_productivity_snapshot(
    user_id: int,
    snapshot_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new productivity snapshot for a specific user.
    
    Args:
        user_id: ID of the user to create snapshot for
        snapshot_date: Date for the snapshot (defaults to today)
    """
    try:
        # Check if user is superuser or project manager
        if not (current_user.get("is_superuser") or current_user.get("is_project_manager")):
            raise HTTPException(
                status_code=403,
                detail="Only administrators and project managers can create productivity snapshots"
            )
        
        if snapshot_date is None:
            snapshot_date = date.today()
            
        # Check if snapshot already exists for this date
        existing_snapshot = db.query(UserProductivityHistory).filter(
            UserProductivityHistory.user_id == user_id,
            UserProductivityHistory.snapshot_date == snapshot_date,
            UserProductivityHistory.period_type == "daily"
        ).first()
        
        if existing_snapshot:
            return {
                "message": "Productivity snapshot already exists for this date",
                "snapshot": existing_snapshot.to_dict()
            }
        
        # Calculate productivity metrics for the specific day
        start_datetime = datetime.combine(snapshot_date, datetime.min.time())
        end_datetime = datetime.combine(snapshot_date, datetime.max.time())
        
        # Get tasks completed on this day
        completed_tasks = db.query(Task).filter(
            Task.assigned_to == user_id,
            Task.state == TaskState.DONE,
            Task.end_date >= start_datetime,
            Task.end_date <= end_datetime
        ).all()
        
        # Get tasks started on this day
        started_tasks = db.query(Task).filter(
            Task.assigned_to == user_id,
            Task.created_at >= start_datetime,
            Task.created_at <= end_datetime
        ).all()
        
        # Get tasks in progress on this day
        in_progress_tasks = db.query(Task).filter(
            Task.assigned_to == user_id,
            Task.state.in_([TaskState.IN_PROGRESS, TaskState.CHANGES_REQUESTED, TaskState.APPROVED]),
            or_(
                and_(Task.start_date <= end_datetime, Task.end_date >= start_datetime),
                and_(Task.start_date.is_(None), Task.created_at <= end_datetime)
            )
        ).all()
        
        # Calculate time spent on this day
        time_entries = db.query(TimeEntry).filter(
            TimeEntry.user_id == user_id,
            TimeEntry.start_time >= start_datetime,
            TimeEntry.start_time <= end_datetime
        ).all()
        
        total_time_spent = sum(entry.duration for entry in time_entries)
        
        # Calculate productivity score for the day
        productivity_score = 0.0
        avg_complexity = 0.0
        avg_completion_time = 0.0
        
        if completed_tasks:
            # Calculate average complexity
            complexity_scores = []
            completion_times = []
            
            for task in completed_tasks:
                if task.complexity_score:
                    complexity_scores.append(task.complexity_score)
                
                if task.start_date and task.end_date:
                    completion_time = (task.end_date - task.start_date).total_seconds() / 3600
                    completion_times.append(completion_time)
            
            avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0.0
            avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0.0
            
            # Simple productivity score: (completed_tasks * avg_complexity) / total_time_spent
            if total_time_spent > 0:
                productivity_score = (len(completed_tasks) * avg_complexity) / total_time_spent
        
        # Calculate completion rate
        total_active_tasks = len(started_tasks) + len(in_progress_tasks)
        completion_rate = (len(completed_tasks) / total_active_tasks * 100) if total_active_tasks > 0 else 0.0
        
        # Calculate trend compared to previous day
        previous_date = snapshot_date - timedelta(days=1)
        previous_snapshot = db.query(UserProductivityHistory).filter(
            UserProductivityHistory.user_id == user_id,
            UserProductivityHistory.snapshot_date == previous_date,
            UserProductivityHistory.period_type == "daily"
        ).first()
        
        trend = "stable"
        trend_percentage = 0.0
        
        if previous_snapshot:
            previous_score = previous_snapshot.productivity_score
            if previous_score > 0:
                trend_percentage = ((productivity_score - previous_score) / previous_score) * 100
                if trend_percentage > 5:
                    trend = "up"
                elif trend_percentage < -5:
                    trend = "down"
        
        # Create new productivity history record
        new_history = UserProductivityHistory(
            user_id=user_id,
            snapshot_date=snapshot_date,
            period_type="daily",
            productivity_score=productivity_score,
            completed_tasks=len(completed_tasks),
            total_time_spent=total_time_spent,
            avg_complexity=avg_complexity,
            tasks_started=len(started_tasks),
            tasks_in_progress=len(in_progress_tasks),
            completion_rate=completion_rate,
            avg_completion_time=avg_completion_time,
            score_trend=trend,
            trend_percentage=trend_percentage
        )
        
        db.add(new_history)
        db.commit()
        
        return {
            "message": "Productivity snapshot created successfully",
            "snapshot": new_history.to_dict()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating productivity snapshot: {str(e)}"
        )

@router.get("/projects/{project_id}/progress/stored")
async def get_stored_project_progress(project_id: int):
    """Fetch the latest stored project progress from Redis."""
    redis_client = get_redis_client()
    result = redis_client.get(f"project_progress:{project_id}")
    if result:
        return result
    return {"status": "not_ready", "message": "No stored progress found for this project. Please trigger calculation."}

@router.get("/tasks/active-risks", response_model=Dict[str, Any])
async def get_active_tasks_with_risks(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all active tasks with their risk levels, sorted by highest risk first.
    
    Returns:
    - List of active tasks with risk analysis
    - Each task includes: risk score, risk level, causes, and mitigation recommendations
    - Sorted by risk score (highest to lowest)
    - Includes AI-generated insights and specific problems
    """
    try:
        # Get active task states
        active_states = ['in_progress', 'approved', 'changes_requested']
        
        # Get all active tasks with their latest risk analysis
        active_tasks_with_risks = []
        
        # Query active tasks
        active_tasks = db.query(Task).filter(
            Task.state.in_(active_states)
        ).all()
        
        task_risk_crud = TaskRiskCRUD(db)
        
        for task in active_tasks:
            # Get latest risk analysis for this task
            latest_risk = task_risk_crud.get_latest_risk_analysis(task.id)
            
            if latest_risk:
                # Extract risk factors and recommendations
                risk_factors = latest_risk.risk_factors or {}
                recommendations = latest_risk.recommendations or {}
                metrics = latest_risk.metrics or {}
                
                # Ensure risk_factors and recommendations are dictionaries
                if not isinstance(risk_factors, dict):
                    risk_factors = {}
                if not isinstance(recommendations, dict):
                    recommendations = {}
                if not isinstance(metrics, dict):
                    metrics = {}
                
                # Prepare risk causes (from risk factors)
                causes = []
                ai_insights = []
                specific_problems = []
                
                if risk_factors:
                    for factor_name, factor_data in risk_factors.items():
                        if isinstance(factor_data, dict):
                            score = factor_data.get('score', 0)
                            details = factor_data.get('details', {})
                            risk_level = factor_data.get('risk_level', 'medium')
                            
                            # Create detailed cause description
                            cause_description = f"{factor_name.replace('_', ' ').title()}: {score:.1f} points"
                            problem_description = ""
                            
                            if details:
                                if isinstance(details, dict):
                                    # Extract specific problems from details
                                    if 'time_risk_percentage' in details:
                                        time_risk = details['time_risk_percentage']
                                        cause_description += f" (Time risk: {time_risk:.1f}%)"
                                        if time_risk > 100:
                                            problem_description = f"Task needs {time_risk:.1f}% more time than available"
                                        elif time_risk > 60:
                                            problem_description = f"Significant time pressure with {time_risk:.1f}% risk"
                                    
                                    elif 'complexity_score' in details:
                                        complexity = details['complexity_score']
                                        cause_description += f" (Complexity: {complexity:.1f})"
                                        if complexity > 70:
                                            problem_description = f"High complexity task requiring specialized skills"
                                        elif complexity > 50:
                                            problem_description = f"Moderate complexity that may need additional resources"
                                    
                                    elif 'dependency_score' in details:
                                        dep_score = details['dependency_score']
                                        cause_description += f" (Dependencies: {dep_score:.1f})"
                                        if dep_score > 5:
                                            problem_description = f"Multiple blocking dependencies affecting progress"
                                        elif dep_score > 2:
                                            problem_description = f"Some dependencies may cause delays"
                                    
                                    # Extract AI analysis if available
                                    if 'ai_analysis' in details:
                                        ai_analysis = details['ai_analysis']
                                        if isinstance(ai_analysis, dict):
                                            if 'insights' in ai_analysis:
                                                ai_insights.extend(ai_analysis['insights'])
                                            if 'problems' in ai_analysis:
                                                specific_problems.extend(ai_analysis['problems'])
                                            if 'warnings' in ai_analysis:
                                                specific_problems.extend(ai_analysis['warnings'])
                                else:
                                    cause_description += f" - {str(details)}"
                            
                            causes.append({
                                "factor": factor_name,
                                "score": score,
                                "description": cause_description,
                                "risk_level": risk_level,
                                "details": details,
                                "problem": problem_description
                            })
                
                # Prepare mitigation recommendations with AI insights
                mitigations = []
                ai_recommendations = []
                
                if recommendations:
                    for category, actions in recommendations.items():
                        if isinstance(actions, list):
                            for action in actions:
                                priority = "immediate" if category == "immediate_actions" else "short_term" if category == "short_term" else "long_term"
                                
                                mitigations.append({
                                    "category": category.replace('_', ' ').title(),
                                    "action": action,
                                    "priority": priority
                                })
                                
                                # Add AI recommendation context
                                ai_recommendations.append({
                                    "priority": priority,
                                    "recommendation": action,
                                    "rationale": f"AI-suggested {priority} action to address {category.replace('_', ' ')} risks"
                                })
                
                # Extract additional AI insights from metrics
                if metrics:
                    if 'ai_insights' in metrics:
                        ai_insights.extend(metrics['ai_insights'])
                    if 'critical_insights' in metrics:
                        ai_insights.extend(metrics['critical_insights'])
                    if 'warning_insights' in metrics:
                        ai_insights.extend(metrics['warning_insights'])
                    if 'problems' in metrics:
                        specific_problems.extend(metrics['problems'])
                    if 'bottlenecks' in metrics:
                        specific_problems.extend(metrics['bottlenecks'])
                
                # Generate task-specific AI insights based on risk factors
                if not ai_insights:
                    if latest_risk.risk_score >= 80:
                        ai_insights.append("CRITICAL: This task requires immediate attention due to extreme risk factors")
                    elif latest_risk.risk_score >= 60:
                        ai_insights.append("HIGH RISK: Multiple risk factors indicate potential failure points")
                    elif latest_risk.risk_score >= 40:
                        ai_insights.append("MODERATE RISK: Some risk factors need monitoring and mitigation")
                
                # Generate specific problems if none found
                if not specific_problems:
                    if latest_risk.time_sensitivity > 25:
                        specific_problems.append("Time pressure: Task may not meet deadline with current progress")
                    if latest_risk.complexity > 15:
                        specific_problems.append("Complexity: Task requires specialized skills or additional resources")
                    if task.progress < 20 and task.start_date:
                        days_since_start = (datetime.now(timezone.utc) - task.start_date).days
                        if days_since_start > 3:
                            specific_problems.append(f"Slow progress: Only {task.progress}% complete after {days_since_start} days")
                
                # Create comprehensive task risk summary
                task_risk_summary = {
                    "task_id": task.id,
                    "task_name": task.name,
                    "task_description": task.description or "",
                    "project_id": task.project_id,
                    "project_name": task.project.name if task.project else "Unknown",
                    "assigned_to": task.assigned_to,
                    "assignee_name": task.assignee.full_name if task.assignee else None,
                    "state": task.state,
                    "progress": task.progress or 0.0,
                    "deadline": task.deadline.isoformat() if task.deadline else None,
                    "planned_hours": task.planned_hours or 0.0,
                    "start_date": task.start_date.isoformat() if task.start_date else None,
                    
                    # Risk analysis data
                    "risk_score": round(latest_risk.risk_score, 2),
                    "risk_level": latest_risk.risk_level,
                    "risk_analysis_date": latest_risk.created_at.isoformat(),
                    
                    # Component scores
                    "time_sensitivity": round(latest_risk.time_sensitivity, 2),
                    "complexity": round(latest_risk.complexity, 2),
                    "priority": round(latest_risk.priority, 2),
                    
                    # AI Analysis and Insights
                    "ai_insights": list(set(ai_insights)),  # Remove duplicates
                    "specific_problems": list(set(specific_problems)),  # Remove duplicates
                    "ai_recommendations": ai_recommendations,
                    
                    # Detailed analysis
                    "causes": sorted(causes, key=lambda x: x['score'], reverse=True),
                    "mitigations": sorted(mitigations, key=lambda x: 0 if x['priority'] == 'immediate' else 1 if x['priority'] == 'short_term' else 2),
                    
                    # Risk factors summary
                    "risk_factors_summary": {
                        "total_factors": len(causes),
                        "high_risk_factors": len([c for c in causes if c['risk_level'] in ['high', 'critical', 'extreme']]),
                        "medium_risk_factors": len([c for c in causes if c['risk_level'] == 'medium']),
                        "low_risk_factors": len([c for c in causes if c['risk_level'] == 'low'])
                    },
                    
                    # Overall assessment
                    "overall_assessment": {
                        "severity": "critical" if latest_risk.risk_score >= 80 else "high" if latest_risk.risk_score >= 60 else "medium" if latest_risk.risk_score >= 40 else "low",
                        "main_concern": max(causes, key=lambda x: x['score'])['factor'] if causes else "No specific concerns",
                        "immediate_actions_needed": len([m for m in mitigations if m['priority'] == 'immediate']),
                        "success_probability": max(0, 100 - latest_risk.risk_score)
                    }
                }
                
                active_tasks_with_risks.append(task_risk_summary)
        
        # Sort by risk score (highest to lowest)
        active_tasks_with_risks.sort(key=lambda x: x['risk_score'], reverse=True)
        
        # Calculate summary statistics
        if active_tasks_with_risks:
            risk_scores = [task['risk_score'] for task in active_tasks_with_risks]
            risk_levels = [task['risk_level'] for task in active_tasks_with_risks]
            
            # Collect all AI insights and problems
            all_ai_insights = []
            all_specific_problems = []
            for task in active_tasks_with_risks:
                all_ai_insights.extend(task.get('ai_insights', []))
                all_specific_problems.extend(task.get('specific_problems', []))
            
            summary_stats = {
                "total_active_tasks": len(active_tasks_with_risks),
                "average_risk_score": round(sum(risk_scores) / len(risk_scores), 2),
                "highest_risk_score": max(risk_scores),
                "lowest_risk_score": min(risk_scores),
                "risk_distribution": {
                    "extreme": risk_levels.count("extreme"),
                    "critical": risk_levels.count("critical"),
                    "high": risk_levels.count("high"),
                    "medium": risk_levels.count("medium"),
                    "low": risk_levels.count("low"),
                    "minimal": risk_levels.count("minimal")
                },
                "tasks_needing_immediate_attention": len([t for t in active_tasks_with_risks if t['risk_score'] >= 70]),
                "tasks_with_high_risk": len([t for t in active_tasks_with_risks if t['risk_score'] >= 50]),
                "total_ai_insights": len(set(all_ai_insights)),
                "total_specific_problems": len(set(all_specific_problems)),
                "critical_insights": list(set([insight for insight in all_ai_insights if "CRITICAL" in insight.upper() or "IMMEDIATE" in insight.upper()])),
                "common_problems": list(set(all_specific_problems))[:5]  # Top 5 common problems
            }
        else:
            summary_stats = {
                "total_active_tasks": 0,
                "average_risk_score": 0,
                "highest_risk_score": 0,
                "lowest_risk_score": 0,
                "risk_distribution": {"extreme": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "minimal": 0},
                "tasks_needing_immediate_attention": 0,
                "tasks_with_high_risk": 0,
                "total_ai_insights": 0,
                "total_specific_problems": 0,
                "critical_insights": [],
                "common_problems": []
            }
        
        return {
            "status": "success",
            "summary": summary_stats,
            "tasks": active_tasks_with_risks,
            "message": f"Found {len(active_tasks_with_risks)} active tasks with comprehensive risk analysis and AI insights"
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error fetching active tasks with risks: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching active tasks with risks: {str(e)}"
        )

@router.get("/tasks/active-risks-summary", response_model=Dict[str, Any])
async def get_active_tasks_risk_summary(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a summary of active tasks with their risk levels, sorted by highest risk first.
    This is a simplified version that shows just the essential risk information.
    
    Returns:
    - List of active tasks with basic risk information
    - Sorted by risk score (highest to lowest)
    - Includes only essential risk data for quick overview
    - Includes AI insights and specific problems
    """
    try:
        # Get active task states
        active_states = ['in_progress', 'approved', 'changes_requested']
        
        # Get all active tasks with their latest risk analysis
        active_tasks_with_risks = []
        
        # Query active tasks
        active_tasks = db.query(Task).filter(
            Task.state.in_(active_states)
        ).all()
        
        task_risk_crud = TaskRiskCRUD(db)
        
        for task in active_tasks:
            # Get latest risk analysis for this task
            latest_risk = task_risk_crud.get_latest_risk_analysis(task.id)
            
            if latest_risk:
                # Extract risk factors and recommendations
                risk_factors = latest_risk.risk_factors or {}
                recommendations = latest_risk.recommendations or {}
                metrics = latest_risk.metrics or {}
                
                # Ensure risk_factors and recommendations are dictionaries
                if not isinstance(risk_factors, dict):
                    risk_factors = {}
                if not isinstance(recommendations, dict):
                    recommendations = {}
                if not isinstance(metrics, dict):
                    metrics = {}
                
                # Prepare AI insights and problems
                ai_insights = []
                specific_problems = []
                
                # Extract AI insights from risk factors
                if risk_factors:
                    for factor_name, factor_data in risk_factors.items():
                        if isinstance(factor_data, dict):
                            details = factor_data.get('details', {})
                            if isinstance(details, dict) and 'ai_analysis' in details:
                                ai_analysis = details['ai_analysis']
                                if isinstance(ai_analysis, dict):
                                    if 'insights' in ai_analysis:
                                        ai_insights.extend(ai_analysis['insights'])
                                    if 'problems' in ai_analysis:
                                        specific_problems.extend(ai_analysis['problems'])
                                    if 'warnings' in ai_analysis:
                                        specific_problems.extend(ai_analysis['warnings'])
                
                # Extract additional AI insights from metrics
                if metrics:
                    if 'ai_insights' in metrics:
                        ai_insights.extend(metrics['ai_insights'])
                    if 'critical_insights' in metrics:
                        ai_insights.extend(metrics['critical_insights'])
                    if 'warning_insights' in metrics:
                        ai_insights.extend(metrics['warning_insights'])
                    if 'problems' in metrics:
                        specific_problems.extend(metrics['problems'])
                    if 'bottlenecks' in metrics:
                        specific_problems.extend(metrics['bottlenecks'])
                
                # Generate task-specific AI insights based on risk factors
                if not ai_insights:
                    if latest_risk.risk_score >= 80:
                        ai_insights.append("CRITICAL: This task requires immediate attention due to extreme risk factors")
                    elif latest_risk.risk_score >= 60:
                        ai_insights.append("HIGH RISK: Multiple risk factors indicate potential failure points")
                    elif latest_risk.risk_score >= 40:
                        ai_insights.append("MODERATE RISK: Some risk factors need monitoring and mitigation")
                
                # Generate specific problems if none found
                if not specific_problems:
                    if latest_risk.time_sensitivity > 25:
                        specific_problems.append("Time pressure: Task may not meet deadline with current progress")
                    if latest_risk.complexity > 15:
                        specific_problems.append("Complexity: Task requires specialized skills or additional resources")
                    if task.progress < 20 and task.start_date:
                        days_since_start = (datetime.now(timezone.utc) - task.start_date).days
                        if days_since_start > 3:
                            specific_problems.append(f"Slow progress: Only {task.progress}% complete after {days_since_start} days")
                
                # Create simplified task risk summary
                task_risk_summary = {
                    "task_id": task.id,
                    "task_name": task.name,
                    "project_name": task.project.name if task.project else "Unknown",
                    "assignee_name": task.assignee.full_name if task.assignee else "Unassigned",
                    "state": task.state,
                    "progress": task.progress or 0.0,
                    "deadline": task.deadline.isoformat() if task.deadline else None,
                    
                    # Risk analysis data
                    "risk_score": round(latest_risk.risk_score, 2),
                    "risk_level": latest_risk.risk_level,
                    "risk_analysis_date": latest_risk.created_at.isoformat(),
                    
                    # AI Analysis and Insights
                    "ai_insights": list(set(ai_insights))[:3],  # Top 3 insights
                    "specific_problems": list(set(specific_problems))[:3],  # Top 3 problems
                    
                    # Top risk factors (simplified)
                    "top_risk_factors": []
                }
                
                # Extract top 3 risk factors
                if risk_factors:
                    factor_scores = []
                    for factor_name, factor_data in risk_factors.items():
                        if isinstance(factor_data, dict):
                            score = factor_data.get('score', 0)
                            factor_scores.append({
                                "factor": factor_name.replace('_', ' ').title(),
                                "score": score
                            })
                    
                    # Sort by score and take top 3
                    factor_scores.sort(key=lambda x: x['score'], reverse=True)
                    task_risk_summary["top_risk_factors"] = factor_scores[:3]
                
                # Add immediate actions needed
                immediate_actions = []
                if recommendations:
                    for category, actions in recommendations.items():
                        if category == "immediate_actions" and isinstance(actions, list):
                            immediate_actions.extend(actions[:2])  # Top 2 immediate actions
                
                task_risk_summary["immediate_actions"] = immediate_actions
                
                # Add overall assessment
                task_risk_summary["overall_assessment"] = {
                    "severity": "critical" if latest_risk.risk_score >= 80 else "high" if latest_risk.risk_score >= 60 else "medium" if latest_risk.risk_score >= 40 else "low",
                    "success_probability": max(0, 100 - latest_risk.risk_score),
                    "needs_attention": latest_risk.risk_score >= 50
                }
                
                active_tasks_with_risks.append(task_risk_summary)
        
        # Sort by risk score (highest to lowest)
        active_tasks_with_risks.sort(key=lambda x: x['risk_score'], reverse=True)
        
        # Calculate summary statistics
        if active_tasks_with_risks:
            risk_scores = [task['risk_score'] for task in active_tasks_with_risks]
            risk_levels = [task['risk_level'] for task in active_tasks_with_risks]
            
            # Collect all AI insights and problems
            all_ai_insights = []
            all_specific_problems = []
            for task in active_tasks_with_risks:
                all_ai_insights.extend(task.get('ai_insights', []))
                all_specific_problems.extend(task.get('specific_problems', []))
            
            summary_stats = {
                "total_active_tasks": len(active_tasks_with_risks),
                "average_risk_score": round(sum(risk_scores) / len(risk_scores), 2),
                "highest_risk_score": max(risk_scores),
                "lowest_risk_score": min(risk_scores),
                "risk_distribution": {
                    "extreme": risk_levels.count("extreme"),
                    "critical": risk_levels.count("critical"),
                    "high": risk_levels.count("high"),
                    "medium": risk_levels.count("medium"),
                    "low": risk_levels.count("low"),
                    "minimal": risk_levels.count("minimal")
                },
                "tasks_needing_immediate_attention": len([t for t in active_tasks_with_risks if t['risk_score'] >= 70]),
                "tasks_with_high_risk": len([t for t in active_tasks_with_risks if t['risk_score'] >= 50]),
                "total_ai_insights": len(set(all_ai_insights)),
                "total_specific_problems": len(set(all_specific_problems)),
                "critical_insights": list(set([insight for insight in all_ai_insights if "CRITICAL" in insight.upper() or "IMMEDIATE" in insight.upper()]))[:3],
                "common_problems": list(set(all_specific_problems))[:5]  # Top 5 common problems
            }
        else:
            summary_stats = {
                "total_active_tasks": 0,
                "average_risk_score": 0,
                "highest_risk_score": 0,
                "lowest_risk_score": 0,
                "risk_distribution": {"extreme": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "minimal": 0},
                "tasks_needing_immediate_attention": 0,
                "tasks_with_high_risk": 0,
                "total_ai_insights": 0,
                "total_specific_problems": 0,
                "critical_insights": [],
                "common_problems": []
            }
        
        return {
            "status": "success",
            "summary": summary_stats,
            "tasks": active_tasks_with_risks,
            "message": f"Found {len(active_tasks_with_risks)} active tasks with risk analysis and AI insights"
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error fetching active tasks risk summary: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching active tasks risk summary: {str(e)}"
        )

@router.get("/tasks/ai-suggestions/personalized", response_model=Dict[str, Any])
async def get_personalized_ai_suggestions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get personalized AI suggestions for the top 3 highest-risk tasks.
    This endpoint:
    1. Always queues a new Celery job to generate new suggestions (does NOT check or return cache)
    2. Returns celery_task_id for status tracking
    The result will be stored in Redis by the Celery task after processing.
    """
    try:
        from tasks.analytics import generate_personalized_ai_suggestions_task
        celery_task = generate_personalized_ai_suggestions_task.delay(
            user_id=current_user["id"],
            is_superuser=current_user.get("is_superuser", False)
        )
        return {
            "status": "queued",
            "user_id": current_user["id"],
            "celery_task_id": celery_task.id,
            "message": "Personalized AI suggestions job queued successfully. Use the celery_task_id to check status.",
            "is_superuser": current_user.get("is_superuser", False),
            "source": "always_new_generation"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error queuing personalized AI suggestions: {str(e)}"
        )

@router.get("/tasks/ai-suggestions/status/{celery_task_id}")
async def get_personalized_ai_suggestions_status(
    celery_task_id: str
) -> Dict[str, Any]:
    """
    Check the status of a personalized AI suggestions job.
    
    Returns:
        Dict containing:
        - task_id: str
        - state: str (PENDING, PROGRESS, SUCCESS, FAILURE, etc.)
        - result: Dict (if completed successfully)
        - meta: Dict (progress information if in progress)
    """
    try:
        from celery.result import AsyncResult
        
        result = AsyncResult(celery_task_id)
        response = {
            "task_id": celery_task_id,
            "state": result.state,
            "result": result.result if result.ready() else None,
            "meta": result.info if hasattr(result, 'info') and result.info else None
        }
        return response
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking personalized AI suggestions status: {str(e)}"
        )

@router.post("/tasks/ai-suggestions/personalized/refresh", response_model=Dict[str, Any])
async def refresh_personalized_ai_suggestions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Manually refresh personalized AI suggestions for the top 3 highest-risk tasks.
    
    This endpoint:
    1. Forces regeneration of personalized AI suggestions
    2. Clears any existing cache
    3. Queues a new background job
    4. Returns job ID for status tracking
    
    Use this when you want fresh suggestions regardless of cache status.
    
    Returns:
        Dict containing:
        - status: "queued"
        - user_id: int
        - celery_task_id: str (for status checking)
    """
    try:
        from services.redis_service import get_redis_client
        from tasks.analytics import generate_personalized_ai_suggestions_task
        
        # Clear existing cache
        redis_client = get_redis_client()
        cache_key = f"personalized_ai_suggestions:{current_user['id']}"
        
        try:
            redis_client.delete(cache_key)
            logger.info(f"Cleared existing cache for user {current_user['id']}")
        except Exception as cache_error:
            logger.warning(f"Error clearing cache for user {current_user['id']}: {str(cache_error)}")
        
        # Queue new task
        celery_task = generate_personalized_ai_suggestions_task.delay(
            user_id=current_user["id"],
            is_superuser=current_user.get("is_superuser", False)
        )
        
        return {
            "status": "queued",
            "user_id": current_user["id"],
            "celery_task_id": celery_task.id,
            "message": "Personalized AI suggestions refresh job queued successfully. Use the celery_task_id to check status.",
            "is_superuser": current_user.get("is_superuser", False),
            "source": "manual_refresh"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error refreshing personalized AI suggestions: {str(e)}"
        )

@router.get("/tasks/ai-suggestions/personalized/cached", response_model=Dict[str, Any])
async def get_cached_personalized_ai_suggestions(
    current_user: dict = Depends(get_current_user)
):
    """
    Get the latest personalized AI suggestions for the user directly from Redis.
    Always return the most recent available result (from personalized_ai_suggestions:{user_id}), regardless of expiration.
    If none exists, return a not found message.
    """
    try:
        from services.redis_service import get_redis_client
        redis_client = get_redis_client()
        cache_key = f"personalized_ai_suggestions:{current_user['id']}"
        cached_data = redis_client.get(cache_key)
        if cached_data:
            # Parse the JSON string if needed
            if isinstance(cached_data, str):
                try:
                    cached_data = json.loads(cached_data)
                except Exception:
                    pass
            return {
                "status": "success",
                "source": "redis_latest",
                "data": cached_data
            }
        else:
            return {
                "status": "not_found",
                "message": "No personalized AI suggestions found for this user."
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting cached suggestions: {str(e)}"
        )