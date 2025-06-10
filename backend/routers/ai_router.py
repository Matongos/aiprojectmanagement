from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List
from datetime import datetime, timedelta

from database import get_db
from services.ai_service import get_ai_service
from models.task import Task
from models.task_risk import TaskRisk

router = APIRouter(
    prefix="/ai",
    tags=["AI Analysis"]
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