from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, extract, text, cast, Float
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
from sqlalchemy import or_, and_
import json

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
from models.user_metrics import UserProductivityMetrics
from tasks.productivity_updater import update_user_productivity
from services.complexity_service import ComplexityService
from models.task_stage import TaskStage
from models.project_member import ProjectMember

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
        fourteen_days_ago = datetime.utcnow() - timedelta(days=14)
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

        # --- New: Get previous 7 days tasks ---
        previous_7days_start = fourteen_days_ago
        previous_7days_end = seven_days_ago
        completed_tasks_prev_7days = base_query.filter(
            Task.state == TaskState.DONE,
            Task.updated_at >= previous_7days_start,
            Task.updated_at < previous_7days_end
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
        prev_7days_avg, _, prev_7days_count = calculate_period_metrics(completed_tasks_prev_7days)

        # --- New: Calculate trend for last 7 days vs previous 7 days ---
        trend = ((last_7days_avg - prev_7days_avg) / prev_7days_avg) if prev_7days_avg > 0 else 0

        # Get tasks needing attention (unchanged for 7 business days)
        attention_query = db.query(func.count(Task.id))
        if not current_user.get("is_superuser"):
            attention_query = attention_query.filter(Task.assigned_to == current_user["id"])
        
        tasks_needing_attention = attention_query.filter(
            Task.state.in_([TaskState.IN_PROGRESS, TaskState.CHANGES_REQUESTED]),
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

@router.get("/ml/project/{project_id}/team-performance", response_model=Dict[str, Any])
async def analyze_team_performance(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get ML-powered team performance analysis"""
    try:
        ml_service = get_ml_service(db)
        return await ml_service.analyze_team_performance(project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ml/project/{project_id}/historical-patterns", response_model=Dict[str, Any])
async def get_historical_patterns(
    project_id: int,
    pattern_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get historical patterns identified in project data"""
    try:
        query = db.query(HistoricalPattern)
        if pattern_type:
            query = query.filter(HistoricalPattern.pattern_type == pattern_type)
        patterns = query.order_by(HistoricalPattern.confidence.desc()).all()
        
        return {
            "project_id": project_id,
            "patterns": [
                {
                    "name": p.pattern_name,
                    "description": p.pattern_description,
                    "type": p.pattern_type,
                    "confidence": p.confidence,
                    "support": p.support,
                    "data": p.pattern_data
                }
                for p in patterns
            ]
        }
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

@router.get("/tasks/completion-times")
async def get_tasks_completion_times(
    days: Optional[int] = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a list of all completed tasks with their completion times and assigned users.
    Shows individual task completion times and overall average.
    """
    try:
        # Check if user is superuser or project manager
        if not (current_user.get("is_superuser") or current_user.get("is_project_manager")):
            raise HTTPException(
                status_code=403,
                detail="Only administrators and project managers can view this data"
            )
            
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get completed tasks with user information
        completed_tasks = db.query(
            Task,
            User
        ).join(
            User,
            Task.assigned_to == User.id
        ).filter(
            Task.state == TaskState.DONE,
            Task.start_date.isnot(None),
            Task.end_date.isnot(None),
            Task.end_date >= start_date
        ).order_by(Task.end_date.desc()).all()
        
        if not completed_tasks:
            return {
                "message": "No completed tasks found in the specified period",
                "tasks": [],
                "average_completion_time": 0,
                "total_tasks": 0
            }
        
        tasks_data = []
        total_time = 0
        
        for task, user in completed_tasks:
            # Calculate completion time in hours
            completion_time = (task.end_date - task.start_date).total_seconds() / 3600
            total_time += completion_time
            
            tasks_data.append({
                "task_id": task.id,
                "task_name": task.name,
                "completion_time_hours": round(completion_time, 2),
                "completed_date": task.end_date.isoformat(),
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email
                },
                "project_id": task.project_id,
                "project_name": task.project.name if task.project else None
            })
        
        average_time = total_time / len(completed_tasks)
        
        return {
            "tasks": tasks_data,
            "average_completion_time": round(average_time, 2),
            "total_tasks": len(completed_tasks),
            "period_days": days
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/projects/{project_id}/progress", response_model=Dict[str, Any])
async def get_project_progress(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get overall project progress based on tasks.
    Uses weighted average based on task complexity and allocated time.
    """
    try:
        # Get current time in UTC
        now = datetime.now(timezone.utc)
        
        # Get project with tasks
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Ensure project dates are timezone-aware
        if project.start_date and project.start_date.tzinfo is None:
            project.start_date = project.start_date.replace(tzinfo=timezone.utc)
        if project.end_date and project.end_date.tzinfo is None:
            project.end_date = project.end_date.replace(tzinfo=timezone.utc)

        # Get all tasks for the project
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        if not tasks:
            return {
                "overall_progress": 0,
                "total_tasks": 0,
                "completed_tasks": 0,
                "tasks_progress": [],
                "progress_by_stage": {},
                "critical_path_progress": 0,
                "blocked_tasks": 0,
                "health_metrics": {
                    "on_track": True,
                    "at_risk": False,
                    "behind_schedule": False
                }
            }

        # Initialize complexity service
        complexity_service = ComplexityService()
        
        # Calculate weighted progress for each task
        weighted_progress = 0
        total_weight = 0
        completed_tasks = 0
        blocked_tasks = 0
        tasks_progress = []
        
        for task in tasks:
            # Get task complexity
            try:
                complexity_analysis = await complexity_service.analyze_task_complexity(db, task.id)
                complexity_score = complexity_analysis.total_score
            except Exception as e:
                print(f"Error getting complexity for task {task.id}: {str(e)}")
                complexity_score = 50  # Default to medium complexity

            # Calculate task weight based on complexity and planned hours
            time_weight = task.planned_hours if task.planned_hours else 8  # Default to 8 hours
            task_weight = (complexity_score / 100) * time_weight  # Normalize complexity to 0-1 and multiply by time

            # For progress, only consider if task is done or not
            task_progress = 100 if task.state == TaskState.DONE else 0
            weighted_progress += task_progress * task_weight
            total_weight += task_weight

            if task.state == TaskState.DONE:
                completed_tasks += 1
                
            # Check if task is blocked
            is_blocked = False
            if task.depends_on:
                incomplete_deps = [dep for dep in task.depends_on if dep.state != TaskState.DONE]
                if incomplete_deps:
                    blocked_tasks += 1
                    is_blocked = True
                    
            # Get task stage name
            stage_name = task.stage.name if task.stage else "No Stage"
            
            # Add task progress details
            tasks_progress.append({
                "task_id": task.id,
                "name": task.name,
                "progress": task_progress,  # Will be either 0 or 100
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
                    
        # Calculate overall progress
        overall_progress = weighted_progress / total_weight if total_weight > 0 else 0
        
        # Get progress by stage
        stages = db.query(TaskStage).filter(TaskStage.project_id == project_id).all()
        progress_by_stage = {}
        
        for stage in stages:
            stage_tasks = [t for t in tasks if t.stage_id == stage.id]
            if stage_tasks:
                # Calculate weighted progress for stage
                stage_weighted_progress = 0
                stage_total_weight = 0
                for task in stage_tasks:
                    task_data = next((t for t in tasks_progress if t["task_id"] == task.id), None)
                    if task_data:
                        stage_weighted_progress += task_data["progress"] * task_data["weight"]
                        stage_total_weight += task_data["weight"]
                
                stage_progress = stage_weighted_progress / stage_total_weight if stage_total_weight > 0 else 0
                progress_by_stage[stage.name] = {
                    "progress": round(stage_progress, 2),
                    "tasks_count": len(stage_tasks),
                    "completed_tasks": len([t for t in stage_tasks if t.state == TaskState.DONE]),
                    "total_weight": round(stage_total_weight, 2)
                }
            else:
                progress_by_stage[stage.name] = {
                    "progress": 0,
                    "tasks_count": 0,
                    "completed_tasks": 0,
                    "total_weight": 0
                }
                
        # Calculate critical path progress
        critical_tasks = []
        for task in tasks:
            if task.depends_on or any(t.depends_on for t in tasks if task in t.depends_on):
                critical_tasks.append(task)
                
        if critical_tasks:
            critical_weighted_progress = 0
            critical_total_weight = 0
            for task in critical_tasks:
                task_data = next((t for t in tasks_progress if t["task_id"] == task.id), None)
                if task_data:
                    critical_weighted_progress += task_data["progress"] * task_data["weight"]
                    critical_total_weight += task_data["weight"]
            
            critical_path_progress = critical_weighted_progress / critical_total_weight if critical_total_weight > 0 else 0
        else:
            critical_path_progress = overall_progress
        
        # Sort tasks_progress by weight and progress
        tasks_progress.sort(key=lambda x: (x["weight"], -x["progress"]), reverse=True)
        
        # Calculate health metrics
        is_behind_schedule = False
        if project.start_date:
            days_since_start = (now - project.start_date).days
            is_behind_schedule = overall_progress < 50 and days_since_start > 7

        is_at_risk = blocked_tasks > 0 or (project.end_date and project.end_date < now)
        
        return {
            "overall_progress": round(overall_progress, 2),
            "total_tasks": len(tasks),
            "completed_tasks": completed_tasks,
            "tasks_progress": tasks_progress,
            "progress_by_stage": progress_by_stage,
            "critical_path_progress": round(critical_path_progress, 2),
            "blocked_tasks": blocked_tasks,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "health_metrics": {
                "on_track": blocked_tasks == 0 and overall_progress >= 50,
                "at_risk": is_at_risk,
                "behind_schedule": is_behind_schedule
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch project progress: {str(e)}"
        )

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

@router.get("/projects/{project_id}/weighted-progress", response_model=Dict[str, Any])
async def get_project_weighted_progress(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Calculate weighted progress for a project based on task planned hours"""
    try:
        # Get project and verify access
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
            
        # Check user has access to project
        if not current_user.get("is_superuser"):
            member = db.query(ProjectMember).filter(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == current_user["id"]
            ).first()
            if not member:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have access to this project"
                )
        
        # Get all tasks for the project
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        
        if not tasks:
            return {
                "weighted_progress": 0,
                "total_planned_hours": 0,
                "completed_hours": 0
            }
        
        total_planned_hours = 0
        total_weighted_progress = 0
        completed_hours = 0
        
        for task in tasks:
            planned_hours = task.planned_hours if task.planned_hours else 8  # Default to 8 hours
            total_planned_hours += planned_hours
            
            # Only count progress as 100 if task is done, otherwise 0
            task_progress = 100 if task.state == TaskState.DONE else 0
            total_weighted_progress += task_progress * planned_hours
            
            if task.state == TaskState.DONE:
                completed_hours += planned_hours
        
        # Calculate weighted progress
        weighted_progress = round(total_weighted_progress / total_planned_hours, 2) if total_planned_hours > 0 else 0
        
        # Update project progress
        project.progress = weighted_progress
        db.commit()
        
        return {
            "weighted_progress": weighted_progress,
            "total_planned_hours": total_planned_hours,
            "completed_hours": completed_hours
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate project progress: {str(e)}"
        )