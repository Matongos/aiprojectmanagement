from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List
from datetime import datetime, timedelta, timezone

from database import get_db
from services.ai_service import get_ai_service
from models.task import Task
from models.task_risk import TaskRisk
from services.redis_service import get_redis_client

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
    Perform comprehensive AI risk analysis on a task.
    
    This endpoint analyzes multiple risk factors including:
    - Role/skill match between assignee and task
    - Time-based risks (deadlines, progress)
    - Dependencies and blockers
    - Workload and resource allocation
    - Project context
    - Communication sentiment
    
    Returns a detailed risk assessment with:
    - Overall risk score
    - Specific risk factors
    - Detailed metrics
    - Actionable recommendations
    - Estimated potential delays
    """
    try:
        ai_service = get_ai_service(db)
        analysis = await ai_service.analyze_task_risk(task_id)
        
        if "error" in analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
            
        return analysis
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing task risk: {str(e)}"
        )

@router.get("/project/{project_id}/tasks/risk")
async def analyze_project_tasks_risk(
    project_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Analyze risk levels for all tasks in a project.
    Returns aggregated risk metrics and identifies high-risk tasks.
    """
    try:
        # Get AI service
        ai_service = get_ai_service(db)
        
        # Get all tasks for the project
        tasks = db.query(Task).filter(Task.project_id == project_id).all()
        if not tasks:
            raise HTTPException(
                status_code=404,
                detail=f"No tasks found for project {project_id}"
            )
            
        # Analyze each task
        task_analyses = []
        high_risk_tasks = []
        total_risk_score = 0
        
        for task in tasks:
            analysis = await ai_service.analyze_task_risk(task.id)
            task_analyses.append(analysis)
            
            if analysis.get("risk_score", 0) > 0.7:  # High risk threshold
                high_risk_tasks.append({
                    "task_id": task.id,
                    "name": task.name,
                    "risk_score": analysis["risk_score"],
                    "risk_factors": analysis["risk_factors"]
                })
                
            total_risk_score += analysis.get("risk_score", 0)
            
        # Calculate project-level metrics
        avg_risk_score = total_risk_score / len(tasks) if tasks else 0
        risk_distribution = {
            "low": len([a for a in task_analyses if a.get("risk_score", 0) < 0.4]),
            "medium": len([a for a in task_analyses if 0.4 <= a.get("risk_score", 0) <= 0.7]),
            "high": len([a for a in task_analyses if a.get("risk_score", 0) > 0.7])
        }
        
        # Generate project-level recommendations
        recommendations = []
        if high_risk_tasks:
            recommendations.append(f"Address {len(high_risk_tasks)} high-risk tasks immediately")
        if risk_distribution["medium"] > len(tasks) * 0.4:
            recommendations.append("Review resource allocation across tasks")
        if avg_risk_score > 0.5:
            recommendations.append("Consider project timeline and resource review")
            
        return {
            "project_id": project_id,
            "overall_risk_score": round(avg_risk_score, 2),
            "risk_distribution": risk_distribution,
            "high_risk_tasks": high_risk_tasks,
            "recommendations": recommendations,
            "task_count": len(tasks),
            "detailed_analyses": task_analyses
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing project tasks: {str(e)}"
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

@router.get("/task/{task_id}/risk/history")
async def get_task_risk_history(
    task_id: int,
    days: int = 7,  # Default to last 7 days
    db: Session = Depends(get_db)
) -> List[Dict]:
    """
    Get historical risk analysis data for a task.
    
    Parameters:
    - task_id: The ID of the task
    - days: Number of days of history to retrieve (default: 7)
    
    Returns a list of risk analyses ordered by date, including:
    - Risk scores over time
    - Risk levels
    - Risk breakdowns (time sensitivity, complexity, priority)
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
            
        # Get risk analyses for the specified time period
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        risk_analyses = db.query(TaskRisk).filter(
            TaskRisk.task_id == task_id,
            TaskRisk.created_at >= cutoff_date
        ).order_by(TaskRisk.created_at.desc()).all()
        
        return [{
            "task_id": analysis.task_id,
            "risk_score": analysis.risk_score,
            "risk_level": analysis.risk_level,
            "risk_breakdown": {
                "time_sensitivity": analysis.time_sensitivity,
                "complexity": analysis.complexity,
                "priority": analysis.priority
            },
            "risk_factors": analysis.risk_factors,
            "recommendations": analysis.recommendations,
            "metrics": analysis.metrics,
            "created_at": analysis.created_at.isoformat()
        } for analysis in risk_analyses]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving risk history: {str(e)}"
        ) 