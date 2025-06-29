from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Any
from datetime import datetime, timedelta, timezone
from celery.result import AsyncResult

from database import get_db
from services.ai_service import get_ai_service
from models.task import Task
from models.task_risk import TaskRisk
from services.redis_service import get_redis_client
from crud.task_risk import TaskRiskCRUD
from schemas.task_risk import TaskRiskAnalysisResponse, TaskRiskHistoryResponse, ProjectRiskSummaryResponse
from tasks.task_risk import calculate_task_risk_analysis_task

router = APIRouter(
    prefix="/ai",
    tags=["AI Analysis"]
)

@router.get("/task/{task_id}/time-risk")
async def calculate_task_time_risk(
    task_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Calculate time-based risk for a task using the formula:
    Risk (%) = (T_alloc / (T_left + ε)) * 100
    
    Where:
    - T_alloc = allocated/planned hours for the task
    - T_left = time left until deadline (in hours)
    - ε = small number (1) to avoid division by zero
    
    The risk increases when T_left is small and can exceed 100% to show true severity:
    - 100% = Task needs exactly the time available
    - 200% = Task needs twice the time available
    - 300% = Task needs three times the time available
    
    Risk levels:
    - 200%+ = Extreme (needs 2x+ more time)
    - 150%+ = Critical (needs 1.5x+ more time)
    - 100%+ = High (needs more time than available)
    - 60-99% = Medium (significant time pressure)
    - 30-59% = Low (moderate time pressure)
    - <30% = Minimal (adequate time available)
    
    Optional: Include actual time passed for urgency calculation
    """
    try:
        # Get task details
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
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
        epsilon = 1  # Small number to avoid division by zero
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
        
        # Prepare response
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
        
        # Store in Redis for later use by main risk analysis
        try:
            redis_client = get_redis_client()
            cache_key = f"task_time_risk:{task_id}"
            # Cache for 1 hour (3600 seconds)
            redis_client.setex(cache_key, 3600, result)
        except Exception as e:
            # Don't fail the request if Redis is unavailable
            result["cache_warning"] = f"Could not cache result: {str(e)}"
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating time risk: {str(e)}"
        )

@router.get("/task/{task_id}/time-risk/cache-status")
async def get_time_risk_cache_status(
    task_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Check the cache status of time risk calculation for a task.
    Shows when the risk was last calculated and when it will update next.
    """
    try:
        ai_service = get_ai_service(db)
        cache_status = ai_service.get_time_risk_cache_status(task_id)
        
        return {
            "task_id": task_id,
            "cache_status": cache_status,
            "current_time": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error checking cache status: {str(e)}"
        )

@router.get("/task/{task_id}/time-risk/result")
async def get_time_risk_result(
    task_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get the cached time risk calculation result for a task.
    If no cached result exists, returns an error suggesting to trigger calculation.
    """
    try:
        ai_service = get_ai_service(db)
        cached_result = ai_service.get_cached_time_risk(task_id)
        
        if cached_result:
            return {
                "task_id": task_id,
                "status": "cached",
                "result": cached_result
            }
        else:
            return {
                "task_id": task_id,
                "status": "not_ready",
                "message": "No cached time risk found for this task. Please trigger calculation using /ai/task/{task_id}/time-risk"
            }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving time risk result: {str(e)}"
        )

@router.get("/task/{task_id}/risk")
async def analyze_task_risk(
    task_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Queue a background job to perform comprehensive AI risk analysis on a task and store results in database.
    
    This endpoint:
    1. Queues a background job to perform comprehensive risk analysis
    2. Returns a job ID for status tracking
    3. The job will perform analysis and store results in the database when complete
    
    The analysis includes multiple risk factors:
    - Role/skill match between assignee and task (20%)
    - Time-based risks (deadlines, progress) (30%)
    - Dependencies and blockers (10%)
    - Workload and resource allocation
    - Project context
    - Communication sentiment (10%)
    - Task complexity (20%)
    - Task priority (20%)
    
    Returns:
        Dict containing:
        - status: "queued"
        - task_id: int
        - celery_task_id: str (for status checking)
    """
    try:
        # Check if task exists
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
            
        # Queue the Celery task with 4-second delay
        celery_task = calculate_task_risk_analysis_task.apply_async(
            args=[task_id], 
            countdown=4  # 4-second delay
        )
        
        return {
            "status": "queued",
            "task_id": task_id,
            "celery_task_id": celery_task.id,
            "message": "Risk analysis job queued successfully with 4-second delay. Use the celery_task_id to check status.",
            "delay_seconds": 4
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error queuing risk analysis: {str(e)}"
        )

@router.get("/project/{project_id}/tasks/risk")
async def analyze_project_tasks_risk(
    project_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Queue background jobs to analyze risk levels for all tasks in a project.
    
    This endpoint:
    1. Gets all tasks for the project
    2. Queues individual risk analysis jobs for each task
    3. Returns a summary of queued jobs
    
    Returns:
        Dict containing:
        - status: "queued"
        - project_id: int
        - total_tasks: int
        - queued_tasks: List of task IDs and their celery task IDs
    """
    try:
        # Get all tasks for the project
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        if not tasks:
            raise HTTPException(
                status_code=404,
                detail=f"No tasks found for project {project_id}"
            )
            
        # Queue risk analysis for each task
        queued_tasks = []
        for task in tasks:
            celery_task = calculate_task_risk_analysis_task.delay(task.id)
            queued_tasks.append({
                    "task_id": task.id,
                "task_name": task.name,
                "celery_task_id": celery_task.id
            })
            
        return {
            "status": "queued",
            "project_id": project_id,
            "total_tasks": len(tasks),
            "queued_tasks": queued_tasks,
            "message": f"Risk analysis queued for {len(tasks)} tasks in project {project_id}. Use individual celery_task_ids to check status."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error queuing project risk analysis: {str(e)}"
        )

@router.get("/projects/{project_id}/risks")
async def analyze_project_risks(
    project_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Perform comprehensive AI risk analysis on an entire project.
    
    Analyzes:
    - Task-level risks and their impact on project
    - Resource allocation and skill matching
    - Timeline feasibility
    - Dependencies and critical paths
    - Team workload distribution
    - Communication patterns
    - Budget implications
    """
    try:
        ai_service = get_ai_service(db)
        return await ai_service.analyze_project_risks(project_id)
    except ValueError as ve:
        raise HTTPException(
            status_code=404,
            detail=str(ve)
        )
    except Exception as e:
        print(f"Error in project risk analysis: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing project risks: {str(e)}"
        )

@router.get("/projects/{project_id}/insights")
async def generate_project_insights(
    project_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Generate comprehensive project insights including:
    - Progress analysis
    - Performance metrics
    - Resource utilization
    - Bottlenecks
    - Success patterns
    - Areas for improvement
    - Team dynamics
    """
    try:
        ai_service = get_ai_service(db)
        return await ai_service.generate_project_insights(project_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating project insights: {str(e)}"
        )

@router.get("/task/{task_id}/risk/stored")
async def get_stored_task_risk(
    task_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Retrieve the most recent stored risk analysis for a task from the database.
    
    This endpoint returns the latest risk analysis that was previously calculated
    and stored in the TaskRisk table, without performing a new analysis.
    
    Returns:
    - Latest risk analysis data
    - Analysis timestamp
    - Component scores
    - Risk factors and recommendations
    """
    try:
        # Verify task exists
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
        
        # Get latest stored risk analysis
        task_risk_crud = TaskRiskCRUD(db)
        latest_risk = task_risk_crud.get_latest_risk_analysis(task_id)
        
        if not latest_risk:
            raise HTTPException(
                status_code=404,
                detail=f"No risk analysis found for task {task_id}. Please run /ai/task/{task_id}/risk first."
            )
        
        return {
            "task_id": task_id,
            "analysis_timestamp": latest_risk.created_at.isoformat(),
            "risk_score": latest_risk.risk_score,
            "risk_level": latest_risk.risk_level,
            
            # Component scores
            "time_sensitivity": latest_risk.time_sensitivity,
            "complexity": latest_risk.complexity,
            "priority": latest_risk.priority,
            
            # Detailed analysis
            "risk_factors": latest_risk.risk_factors or {},
            "recommendations": latest_risk.recommendations or {},
            "metrics": latest_risk.metrics,
            
            # Metadata
            "database_record_id": latest_risk.id,
            "data_source": "stored_analysis"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving stored risk analysis: {str(e)}"
        )

@router.get("/task/{task_id}/risk/history")
async def get_task_risk_history(
    task_id: int,
    days: int = 7,  # Default to last 7 days
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get historical risk analysis data for a task from the database.
    
    Parameters:
    - task_id: The ID of the task
    - days: Number of days of history to retrieve (default: 7)
    
    Returns a list of risk analyses ordered by date, including:
    - Risk scores over time
    - Risk levels
    - Component breakdowns
    - Risk factors at each point
    - Recommendations history
    """
    try:
        # Verify task exists
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
            
        # Get risk analysis history
        task_risk_crud = TaskRiskCRUD(db)
        risk_history = task_risk_crud.get_risk_analysis_history(task_id, days)
        
        if not risk_history:
            raise HTTPException(
                status_code=404,
                detail=f"No risk analysis history found for task {task_id} in the last {days} days"
            )
        
        # Calculate statistics
        risk_scores = [risk.risk_score for risk in risk_history]
        avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0
        
        # Determine trend
        if len(risk_scores) >= 2:
            if risk_scores[0] > risk_scores[-1] + 5:
                trend = "decreasing"
            elif risk_scores[0] < risk_scores[-1] - 5:
                trend = "increasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        # Format history data
        history_data = []
        for risk in risk_history:
            history_data.append({
                "analysis_timestamp": risk.created_at.isoformat(),
                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "time_sensitivity": risk.time_sensitivity,
                "complexity": risk.complexity,
                "priority": risk.priority,
                "risk_factors": risk.risk_factors or {},
                "recommendations": risk.recommendations or {},
                "database_record_id": risk.id
            })
        
        return {
            "task_id": task_id,
            "history_period_days": days,
            "total_analyses": len(risk_history),
            "average_risk_score": round(avg_risk_score, 2),
            "risk_trend": trend,
            "history": history_data,
            "statistics": {
                "highest_risk_score": max(risk_scores) if risk_scores else 0,
                "lowest_risk_score": min(risk_scores) if risk_scores else 0,
                "risk_level_distribution": {
                    "minimal": len([r for r in risk_history if r.risk_level == "minimal"]),
                    "low": len([r for r in risk_history if r.risk_level == "low"]),
                    "medium": len([r for r in risk_history if r.risk_level == "medium"]),
                    "high": len([r for r in risk_history if r.risk_level == "high"]),
                    "critical": len([r for r in risk_history if r.risk_level == "critical"]),
                    "extreme": len([r for r in risk_history if r.risk_level == "extreme"])
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving risk history: {str(e)}"
        )

@router.get("/project/{project_id}/risks/stored")
async def get_project_stored_risks(
    project_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get stored risk analyses for all tasks in a project.
    
    Returns:
    - Risk summary for the project
    - Individual task risk data
    - Risk distribution statistics
    - High-risk task identification
    """
    try:
        # Get project tasks
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        if not tasks:
            raise HTTPException(
                status_code=404,
                detail=f"No tasks found for project {project_id}"
            )
        
        # Get risk analyses for all tasks
        task_risk_crud = TaskRiskCRUD(db)
        project_risks = task_risk_crud.get_project_risk_analyses(project_id)
        
        if not project_risks:
            raise HTTPException(
                status_code=404,
                detail=f"No risk analyses found for project {project_id}. Please run risk analysis on individual tasks first."
            )
        
        # Get statistics
        risk_statistics = task_risk_crud.get_risk_statistics(project_id)
        
        # Get high-risk tasks
        high_risk_tasks = task_risk_crud.get_high_risk_tasks(threshold=0.6)
        project_high_risk_tasks = [r for r in high_risk_tasks if r.task.project_id == project_id]
        
        # Format task risk data
        task_risks = []
        for risk in project_risks:
            task_risks.append({
                "task_id": risk.task_id,
                "task_name": risk.task.name if risk.task else "Unknown Task",
                "analysis_timestamp": risk.created_at.isoformat(),
                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "time_sensitivity": risk.time_sensitivity,
                "complexity": risk.complexity,
                "priority": risk.priority,
                "database_record_id": risk.id
            })
        
        # Generate recommendations
        recommendations = []
        if risk_statistics["average_risk_score"] > 50:
            recommendations.append("Project has high overall risk - consider timeline review")
        if len(project_high_risk_tasks) > len(tasks) * 0.3:
            recommendations.append("High proportion of risky tasks - review resource allocation")
        if risk_statistics["risk_distribution"]["critical"] > 0 or risk_statistics["risk_distribution"]["extreme"] > 0:
            recommendations.append("Critical/extreme risk tasks detected - immediate attention required")
        
        return {
            "project_id": project_id,
            "total_tasks": len(tasks),
            "analyzed_tasks": len(project_risks),
            "average_risk_score": round(risk_statistics["average_risk_score"], 2),
            "risk_distribution": risk_statistics["risk_distribution"],
            "high_risk_tasks": [
                {
                    "task_id": risk.task_id,
                    "task_name": risk.task.name if risk.task else "Unknown Task",
                    "risk_score": risk.risk_score,
                    "risk_level": risk.risk_level
                } for risk in project_high_risk_tasks
            ],
            "recommendations": recommendations,
            "task_risks": task_risks,
            "statistics": risk_statistics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving project risks: {str(e)}"
        )

@router.get("/test/task-risks-table")
async def test_task_risks_table(db: Session = Depends(get_db)) -> Dict:
    """
    Test endpoint to check if the task_risks table exists and is accessible.
    """
    try:
        # Try to query the table
        result = db.execute("SELECT COUNT(*) FROM task_risks").scalar()
        return {
            "status": "success",
            "message": "Task risks table exists and is accessible",
            "record_count": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Task risks table error: {str(e)}",
            "error_type": type(e).__name__
        }

@router.get("/task/{task_id}/risk/status/{celery_task_id}")
async def get_risk_analysis_status(
    task_id: int,
    celery_task_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Check the status of a risk analysis job.
    
    Returns:
        Dict containing:
        - task_id: str
        - state: str (PENDING, PROGRESS, SUCCESS, FAILURE, etc.)
        - result: Dict (if completed successfully)
        - meta: Dict (progress information if in progress)
    """
    try:
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
            detail=f"Error checking risk analysis status: {str(e)}"
        )

@router.post("/project/{project_id}/tasks/risk/batch")
async def analyze_project_tasks_risk_batch(
    project_id: int,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Queue background jobs to analyze risk levels for all tasks in a project.
    
    This endpoint:
    1. Gets all tasks for the project
    2. Queues individual risk analysis jobs for each task
    3. Returns a summary of queued jobs
    
    Returns:
        Dict containing:
        - status: "queued"
        - project_id: int
        - total_tasks: int
        - queued_tasks: List of task IDs and their celery task IDs
    """
    try:
        # Get all tasks for the project
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        if not tasks:
            raise HTTPException(
                status_code=404,
                detail=f"No tasks found for project {project_id}"
            )
            
        # Queue risk analysis for each task
        queued_tasks = []
        for task in tasks:
            celery_task = calculate_task_risk_analysis_task.delay(task.id)
            queued_tasks.append({
                "task_id": task.id,
                "task_name": task.name,
                "celery_task_id": celery_task.id
            })
            
        return {
            "status": "queued",
            "project_id": project_id,
            "total_tasks": len(tasks),
            "queued_tasks": queued_tasks,
            "message": f"Risk analysis queued for {len(tasks)} tasks in project {project_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error queuing project risk analysis: {str(e)}"
        ) 