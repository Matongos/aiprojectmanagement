from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, List, Any
from datetime import datetime, timedelta, timezone
from celery.result import AsyncResult
import json
import redis

from database import get_db
from routers.auth import get_current_user
from services.ai_service import get_ai_service
from models.task import Task
from models.user import User
from models.task_risk import TaskRisk
from services.redis_service import get_redis_client
from crud.task_risk import TaskRiskCRUD
from schemas.task_risk import TaskRiskAnalysisResponse, TaskRiskHistoryResponse, ProjectRiskSummaryResponse
from tasks.task_risk import calculate_task_risk_analysis_task
from tasks.analytics import optimize_resources_task

router = APIRouter(
    prefix="/ai",
    tags=["AI Analysis"]
)

redis_client = redis.Redis(host='localhost', port=6379, db=0)

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
    Get cached time risk result for a task
    """
    try:
        redis_client = get_redis_client()
        cache_key = f"task_time_risk:{task_id}"
        cached_result = redis_client.get(cache_key)
        
        if cached_result:
            return {
                "status": "success",
                "source": "cached",
                "data": cached_result
            }
        else:
            return {
                "status": "not_found",
                "message": "No cached time risk data found for this task"
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving cached time risk: {str(e)}"
        )

@router.get("/tasks/time-risk/all-active")
async def calculate_all_active_tasks_time_risk(
    project_id: int = None,  # Optional: filter by project
    db: Session = Depends(get_db)
) -> Dict:
    """
    Calculate time-based risk for ALL active tasks at once.
    Uses the same logic as individual task time risk but processes multiple tasks efficiently.
    
    Optional query parameter:
    - project_id: Filter tasks by specific project
    
    Returns comprehensive time risk analysis for all active tasks.
    """
    try:
        # Get current time with timezone awareness
        now = datetime.now(timezone.utc)
        
        # Build query for active tasks
        query = db.query(Task).filter(
            Task.state.in_(['in_progress', 'approved', 'changes_requested'])
        )
        
        # Filter by project if specified
        if project_id:
            query = query.filter(Task.project_id == project_id)
        
        # Get all active tasks
        active_tasks = query.all()
        
        if not active_tasks:
            return {
                "status": "success",
                "message": "No active tasks found",
                "total_tasks": 0,
                "tasks_analyzed": 0,
                "analysis_timestamp": now.isoformat(),
                "results": []
            }
        
        # Process each task using the same logic as individual endpoint
        results = []
        total_risk_score = 0
        risk_distribution = {
            "extreme": 0,
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
            "minimal": 0
        }
        
        for task in active_tasks:
            try:
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
                
                # Update risk distribution
                risk_distribution[risk_level] += 1
                total_risk_score += final_risk
                
                # Prepare task result
                task_result = {
                    "task_id": task.id,
                    "task_name": task.name,
                    "project_id": task.project_id,
                    "project_name": task.project.name if task.project else "Unknown",
                    "assignee_id": task.assigned_to,
                    "assignee_name": task.assignee.full_name if task.assignee else "Unassigned",
                    "state": task.state,
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
                    "calculation_timestamp": now.isoformat()
                }
                
                results.append(task_result)
                
            except Exception as task_error:
                # Log error but continue processing other tasks
                results.append({
                    "task_id": task.id,
                    "task_name": task.name,
                    "error": f"Failed to calculate time risk: {str(task_error)}",
                    "calculation_timestamp": now.isoformat()
                })
        
        # Calculate summary statistics
        successful_analyses = len([r for r in results if "error" not in r])
        average_risk_score = total_risk_score / successful_analyses if successful_analyses > 0 else 0
        
        # Sort results by risk level (highest risk first)
        risk_level_order = {"extreme": 6, "critical": 5, "high": 4, "medium": 3, "low": 2, "minimal": 1}
        results.sort(key=lambda x: risk_level_order.get(x.get("risk_level", "minimal"), 0), reverse=True)
        
        # Prepare comprehensive response
        response = {
            "status": "success",
            "total_tasks": len(active_tasks),
            "tasks_analyzed": successful_analyses,
            "analysis_timestamp": now.isoformat(),
            "summary": {
                "average_risk_score": round(average_risk_score, 2),
                "highest_risk_score": max([r.get("time_risk_percentage", 0) for r in results if "error" not in r], default=0),
                "lowest_risk_score": min([r.get("time_risk_percentage", 0) for r in results if "error" not in r], default=0),
                "risk_distribution": risk_distribution,
                "overdue_tasks": len([r for r in results if r.get("time_data", {}).get("is_overdue", False)]),
                "critical_tasks": risk_distribution["extreme"] + risk_distribution["critical"] + risk_distribution["high"]
            },
            "results": results
        }
        
        # Cache the results in Redis for quick access
        try:
            redis_client = get_redis_client()
            cache_key = f"all_active_tasks_time_risk:{project_id or 'all'}"
            # Cache for 30 minutes (1800 seconds)
            redis_client.setex(cache_key, 1800, response)
        except Exception as e:
            # Don't fail the request if Redis is unavailable
            response["cache_warning"] = f"Could not cache results: {str(e)}"
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating time risk for all active tasks: {str(e)}"
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

@router.get("/tasks/suggest-optimized-due-dates")
async def suggest_optimized_due_dates(
    project_id: int = None,  # Optional: filter by project
    target_risk_range: str = "20-50",  # Default optimal range
    db: Session = Depends(get_db)
) -> Dict:
    """
    Suggest optimized due dates for tasks based on their current time risk scores.
    
    This endpoint analyzes all active tasks and suggests new due dates to achieve
    optimal time risk scores (default: 20-50%).
    
    Query Parameters:
    - project_id: Optional - Filter tasks by specific project
    - target_risk_range: Optional - Target risk range (e.g., "20-50", "30-60")
    
    The endpoint identifies:
    1. Tasks with very low time risk (< 15%) - can be moved closer
    2. Tasks with very high time risk (> 80%) - need more time
    3. Tasks with extreme risk (> 150%) - urgent rescheduling needed
    
    Returns comprehensive optimization suggestions with impact analysis.
    """
    try:
        # Parse target risk range
        try:
            min_target, max_target = map(float, target_risk_range.split("-"))
        except ValueError:
            min_target, max_target = 20.0, 50.0  # Default fallback
        
        # Get current time with timezone awareness
        now = datetime.now(timezone.utc)
        
        # Build query for active tasks
        query = db.query(Task).filter(
            Task.state.in_(['in_progress', 'approved', 'changes_requested'])
        )
        
        # Filter by project if specified
        if project_id:
            query = query.filter(Task.project_id == project_id)
        
        # Get all active tasks
        active_tasks = query.all()
        
        if not active_tasks:
            return {
                "status": "success",
                "message": "No active tasks found",
                "total_tasks": 0,
                "tasks_analyzed": 0,
                "analysis_timestamp": now.isoformat(),
                "suggestions": []
            }
        
        # Process each task and generate optimization suggestions
        suggestions = []
        optimization_summary = {
            "tasks_needing_earlier_deadline": 0,
            "tasks_needing_later_deadline": 0,
            "tasks_optimal": 0,
            "total_risk_reduction": 0,
            "average_risk_improvement": 0
        }
        
        for task in active_tasks:
            try:
                # Calculate current time risk using the same logic
                allocated_hours = task.planned_hours or 0
                start_date = task.start_date
                deadline = task.deadline
                
                # Ensure timezone awareness
                def make_timezone_aware(dt):
                    if dt is None:
                        return None
                    if dt.tzinfo is None:
                        return dt.replace(tzinfo=timezone.utc)
                    return dt
                
                start_date = make_timezone_aware(start_date)
                deadline = make_timezone_aware(deadline)
                
                # Calculate current time risk
                if not deadline:
                    current_risk = 0
                    time_left_hours = 0
                    is_overdue = False
                else:
                    time_left = deadline - now
                    time_left_hours = max(0, time_left.total_seconds() / 3600)
                    is_overdue = time_left.total_seconds() < 0
                    
                    # Calculate current risk
                    epsilon = 1
                    if time_left_hours <= 0:
                        overdue_hours = abs(time_left_hours)
                        current_risk = (allocated_hours / (overdue_hours + epsilon)) * 100
                    else:
                        current_risk = (allocated_hours / (time_left_hours + epsilon)) * 100
                
                # Determine if optimization is needed
                optimization_needed = False
                optimization_type = None
                reason = None
                
                if current_risk < 15:
                    optimization_needed = True
                    optimization_type = "move_closer"
                    reason = "Very low time risk - deadline can be moved closer"
                elif current_risk > 80:
                    optimization_needed = True
                    optimization_type = "extend_deadline"
                    reason = "High time risk - needs more time"
                elif current_risk > 150:
                    optimization_needed = True
                    optimization_type = "urgent_extend"
                    reason = "Extreme time risk - urgent rescheduling needed"
                
                # Calculate suggested deadline
                suggested_deadline = None
                suggested_risk = current_risk
                risk_improvement = 0
                
                if optimization_needed and allocated_hours > 0:
                    # Calculate optimal time needed based on target risk
                    target_risk = (min_target + max_target) / 2  # Use middle of range
                    
                    # Calculate required time: T_required = T_alloc / (target_risk / 100) - ε
                    epsilon = 1
                    required_hours = (allocated_hours / (target_risk / 100)) - epsilon
                    required_hours = max(required_hours, allocated_hours * 0.5)  # Minimum 50% of allocated time
                    
                    # Calculate suggested deadline
                    suggested_deadline = now + timedelta(hours=required_hours)
                    
                    # Calculate suggested risk
                    suggested_risk = (allocated_hours / (required_hours + epsilon)) * 100
                    risk_improvement = current_risk - suggested_risk
                
                # Prepare suggestion
                suggestion = {
                    "task_id": task.id,
                    "task_name": task.name,
                    "project_id": task.project_id,
                    "project_name": task.project.name if task.project else "Unknown",
                    "assignee_id": task.assigned_to,
                    "assignee_name": task.assignee.full_name if task.assignee else "Unassigned",
                    "current_state": {
                        "deadline": deadline.isoformat() if deadline else None,
                        "allocated_hours": allocated_hours,
                        "time_left_hours": round(time_left_hours, 2),
                        "current_risk_score": round(current_risk, 2),
                        "is_overdue": is_overdue
                    },
                    "optimization_needed": optimization_needed,
                    "optimization_type": optimization_type,
                    "reason": reason,
                    "suggestion": {
                        "suggested_deadline": suggested_deadline.isoformat() if suggested_deadline else None,
                        "suggested_risk_score": round(suggested_risk, 2),
                        "risk_improvement": round(risk_improvement, 2),
                        "days_change": round((suggested_deadline - deadline).total_seconds() / 86400, 1) if suggested_deadline and deadline else 0
                    },
                    "priority": "high" if current_risk > 150 else "medium" if current_risk > 80 else "low",
                    "analysis_timestamp": now.isoformat()
                }
                
                suggestions.append(suggestion)
                
                # Update summary
                if optimization_needed:
                    if optimization_type in ["move_closer"]:
                        optimization_summary["tasks_needing_earlier_deadline"] += 1
                    else:
                        optimization_summary["tasks_needing_later_deadline"] += 1
                    optimization_summary["total_risk_reduction"] += risk_improvement
                else:
                    optimization_summary["tasks_optimal"] += 1
                
            except Exception as task_error:
                # Log error but continue processing other tasks
                suggestions.append({
                    "task_id": task.id,
                    "task_name": task.name,
                    "error": f"Failed to analyze task: {str(task_error)}",
                    "analysis_timestamp": now.isoformat()
                })
        
        # Calculate summary statistics
        successful_analyses = len([s for s in suggestions if "error" not in s])
        optimization_summary["average_risk_improvement"] = (
            optimization_summary["total_risk_reduction"] / 
            (optimization_summary["tasks_needing_earlier_deadline"] + optimization_summary["tasks_needing_later_deadline"])
            if (optimization_summary["tasks_needing_earlier_deadline"] + optimization_summary["tasks_needing_later_deadline"]) > 0 
            else 0
        )
        
        # Sort suggestions by priority and risk improvement
        suggestions.sort(key=lambda x: (
            {"high": 3, "medium": 2, "low": 1}.get(x.get("priority", "low"), 0),
            x.get("suggestion", {}).get("risk_improvement", 0)
        ), reverse=True)
        
        # Prepare comprehensive response
        response = {
            "status": "success",
            "total_tasks": len(active_tasks),
            "tasks_analyzed": successful_analyses,
            "target_risk_range": f"{min_target}-{max_target}%",
            "analysis_timestamp": now.isoformat(),
            "optimization_summary": {
                "tasks_needing_optimization": optimization_summary["tasks_needing_earlier_deadline"] + optimization_summary["tasks_needing_later_deadline"],
                "tasks_optimal": optimization_summary["tasks_optimal"],
                "tasks_needing_earlier_deadline": optimization_summary["tasks_needing_earlier_deadline"],
                "tasks_needing_later_deadline": optimization_summary["tasks_needing_later_deadline"],
                "total_risk_reduction": round(optimization_summary["total_risk_reduction"], 2),
                "average_risk_improvement": round(optimization_summary["average_risk_improvement"], 2)
            },
            "suggestions": suggestions
        }
        
        # Cache the results in Redis for quick access
        try:
            redis_client = get_redis_client()
            cache_key = f"optimized_due_dates:{project_id or 'all'}:{target_risk_range}"
            # Cache for 15 minutes (900 seconds)
            redis_client.setex(cache_key, 900, response)
        except Exception as e:
            # Don't fail the request if Redis is unavailable
            response["cache_warning"] = f"Could not cache results: {str(e)}"
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error suggesting optimized due dates: {str(e)}"
        )

@router.post("/tasks/apply-optimized-due-dates")
async def apply_optimized_due_dates(
    task_updates: List[Dict],  # List of {task_id, new_deadline, reason}
    db: Session = Depends(get_db)
) -> Dict:
    """
    Apply suggested optimized due dates to tasks.
    
    This endpoint takes a list of task updates and applies the new deadlines.
    Each update should contain:
    - task_id: ID of the task to update
    - new_deadline: ISO format datetime string for the new deadline
    - reason: Optional reason for the change
    
    Returns summary of applied changes and any errors.
    """
    try:
        results = []
        successful_updates = 0
        failed_updates = 0
        
        for update in task_updates:
            try:
                task_id = update.get("task_id")
                new_deadline_str = update.get("new_deadline")
                reason = update.get("reason", "AI-optimized deadline")
                
                if not task_id or not new_deadline_str:
                    results.append({
                        "task_id": task_id,
                        "status": "failed",
                        "error": "Missing task_id or new_deadline"
                    })
                    failed_updates += 1
                    continue
                
                # Get task from database
                task = db.query(Task).filter(Task.id == task_id).first()
                if not task:
                    results.append({
                        "task_id": task_id,
                        "status": "failed",
                        "error": "Task not found"
                    })
                    failed_updates += 1
                    continue
                
                # Parse new deadline
                try:
                    new_deadline = datetime.fromisoformat(new_deadline_str.replace('Z', '+00:00'))
                    if new_deadline.tzinfo is None:
                        new_deadline = new_deadline.replace(tzinfo=timezone.utc)
                except ValueError:
                    results.append({
                        "task_id": task_id,
                        "status": "failed",
                        "error": "Invalid deadline format"
                    })
                    failed_updates += 1
                    continue
                
                # Store old deadline for comparison
                old_deadline = task.deadline
                
                # Update task deadline
                task.deadline = new_deadline
                
                # Add activity log or comment about the change
                # (You can implement this based on your activity logging system)
                
                # Commit the change
                db.commit()
                
                results.append({
                    "task_id": task_id,
                    "task_name": task.name,
                    "status": "success",
                    "old_deadline": old_deadline.isoformat() if old_deadline else None,
                    "new_deadline": new_deadline.isoformat(),
                    "reason": reason,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
                successful_updates += 1
                
            except Exception as update_error:
                db.rollback()
                results.append({
                    "task_id": update.get("task_id"),
                    "status": "failed",
                    "error": f"Update failed: {str(update_error)}"
                })
                failed_updates += 1
        
        return {
            "status": "completed",
            "total_updates": len(task_updates),
            "successful_updates": successful_updates,
            "failed_updates": failed_updates,
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error applying optimized due dates: {str(e)}"
        )

@router.get("/projects/{project_id}/optimize-timeline/latest")
async def get_latest_timeline_optimization(
    project_id: int,
    db: Session = Depends(get_db)
):
    """
    Fetch the latest optimized due dates for all tasks in a project by calling the suggest_optimized_due_dates logic (not Redis).
    Returns: { "suggested_schedule": [ { "task_id": int, "new_due_date": str }, ... ] }
    """
    try:
        # Call the suggest_optimized_due_dates logic directly
        result = await suggest_optimized_due_dates(project_id=project_id, db=db)
        # Reformat the result to the expected format
        suggested_schedule = []
        for suggestion in result.get("suggestions", []):
            # Only include suggestions with a suggested deadline
            new_due_date = suggestion.get("suggestion", {}).get("suggested_deadline")
            if new_due_date:
                suggested_schedule.append({
                    "task_id": suggestion["task_id"],
                    "new_due_date": new_due_date
                })
        return {"suggested_schedule": suggested_schedule}
    except Exception as e:
        return {"suggested_schedule": [], "error": str(e)}

@router.get("/projects/{project_id}/optimize-resources")
async def start_optimize_resources(project_id: int):
    celery_task = optimize_resources_task.delay(project_id)
    return {"celery_task_id": celery_task.id, "status": "queued"}

@router.get("/projects/{project_id}/optimize-resources/status/{celery_task_id}")
async def get_optimize_resources_status(project_id: int, celery_task_id: str):
    result = AsyncResult(celery_task_id)
    if result.state == "PENDING":
        return {"status": "pending"}
    elif result.state == "SUCCESS":
        return {"status": "success", "result": result.result}
    elif result.state == "FAILURE":
        return {"status": "failure", "error": str(result.result)}
    else:
        return {"status": result.state.lower()}

@router.get("/personalized-ai-suggestions/{user_id}")
async def get_personalized_ai_suggestions(user_id: int):
    """
    Retrieve personalized AI suggestions for a user.
    
    This endpoint retrieves suggestions based on the user's preferences and history.
    
    Returns:
        Dict containing:
        - status: str
        - source: str
        - data: Dict
    """
    try:
        redis_client = get_redis_client()
        cache_key = f"personalized_ai_suggestions:{user_id}"
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
            detail=f"Error retrieving personalized AI suggestions: {str(e)}"
        )

@router.get("/projects/{project_id}/optimize-resources/latest")
async def get_latest_resource_suggestion(project_id: int):
    redis_key = f"ai_assignment_suggestion:project:{project_id}"
    cached = redis_client.get(redis_key)
    if cached:
        return json.loads(cached)
    else:
        return {"status": "not_found"}

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