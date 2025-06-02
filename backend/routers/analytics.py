from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, case, extract, text
from datetime import datetime, timedelta
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
def get_user_productivity(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get current user's productivity metrics
    """
    try:
        analytics_service = AnalyticsService(db)
        return analytics_service.get_user_productivity(current_user["id"])
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
    """Get specific user's productivity metrics"""
    try:
        # Calculate tasks completed in last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        completed_tasks = db.query(func.count(Task.id)).filter(
            Task.assigned_to == user_id,
            Task.state == TaskState.DONE,
            Task.updated_at >= thirty_days_ago
        ).scalar()

        # Calculate average completion time
        task_completion_times = db.query(
            func.avg(
                func.extract('epoch', Task.updated_at - Task.created_at)
            )
        ).filter(
            Task.assigned_to == user_id,
            Task.state == TaskState.DONE
        ).scalar()

        avg_completion_time = round(task_completion_times / 3600, 2) if task_completion_times else 0

        # Get time logged in the last 30 days
        time_logged = db.query(func.sum(TimeEntry.duration)).filter(
            TimeEntry.user_id == user_id,
            TimeEntry.date >= thirty_days_ago
        ).scalar() or 0

        return {
            "tasks_completed_30d": completed_tasks,
            "avg_completion_time_hours": avg_completion_time,
            "time_logged_hours": round(time_logged / 3600, 2)
        }
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
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get daily task creation counts
        created_tasks_query = db.query(
            func.date_trunc('day', Task.created_at).label('date'),
            func.count(Task.id).label('count')
        ).filter(
            Task.created_at >= start_date
        ).group_by(text('date')).order_by(text('date')).all()

        # Get daily task completion counts
        completed_tasks_query = db.query(
            func.date_trunc('day', Task.updated_at).label('date'),
            func.count(Task.id).label('count')
        ).filter(
            Task.state == TaskState.DONE,
            Task.updated_at >= start_date
        ).group_by(text('date')).order_by(text('date')).all()

        # Convert to the expected format
        created_tasks = []
        completed_tasks = []

        # Create a dictionary to store counts by date
        created_by_date = {date: count for date, count in created_tasks_query}
        completed_by_date = {date: count for date, count in completed_tasks_query}

        # Generate a list of all dates in the range
        current_date = start_date
        while current_date <= datetime.utcnow():
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
            Task.updated_at >= start_date
        ).all()
        
        # Calculate metrics
        total_completed = len(completed_tasks)
        total_time = sum(
            sum(entry.duration for entry in task.time_entries)
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