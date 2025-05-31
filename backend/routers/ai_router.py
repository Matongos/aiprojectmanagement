from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List

from database import get_db
from services.ai_service import get_ai_service
from models.task import Task

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

@router.get("/tasks/{task_id}/risk")
async def analyze_task_risk_endpoint(
    task_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Analyze risk factors for a specific task.
    
    Returns comprehensive risk analysis including:
    - Overall risk score
    - Risk factors breakdown
    - Role-skill match analysis
    - Timeline analysis
    - Dependency analysis
    - Workload impact
    - Recommendations
    """
    try:
        ai_service = get_ai_service(db)
        analysis = await ai_service.analyze_task_risk(task_id)
        
        if "error" in analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found"
            )
            
        return {
            "task_id": task_id,
            "risk_score": analysis.get("risk_score", 0),
            "is_at_risk": analysis.get("at_risk", False),
            "risk_factors": analysis.get("risk_factors", []),
            "metrics": {
                "time": analysis.get("metrics", {}).get("time", {}),
                "role_match": analysis.get("metrics", {}).get("role_match", {}),
                "dependencies": analysis.get("metrics", {}).get("dependencies", {}),
                "workload": analysis.get("metrics", {}).get("workload", {}),
                "activity": analysis.get("metrics", {}).get("activity", {}),
                "sentiment": analysis.get("metrics", {}).get("sentiment", {})
            },
            "recommendations": analysis.get("recommendations", []),
            "estimated_delay_days": analysis.get("estimated_delay_days", 0),
            "updated_at": analysis.get("updated_at")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing task risk: {str(e)}"
        )

@router.get("/tasks/{task_id}/risk/detailed")
async def analyze_task_risk_detailed(
    task_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Get detailed risk analysis for a task with all raw metrics and calculations.
    Useful for debugging or understanding how risk is calculated.
    """
    try:
        ai_service = get_ai_service(db)
        return await ai_service.analyze_task_risk(task_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing task risk: {str(e)}"
        )

@router.get("/tasks/{task_id}/analyze")
async def analyze_task(
    task_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Perform comprehensive analysis of a task including:
    - Task complexity
    - Required skills
    - Potential challenges
    - Success factors
    - Best practices
    """
    try:
        ai_service = get_ai_service(db)
        return await ai_service.analyze_task(task_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing task: {str(e)}"
        )

@router.get("/tasks/{task_id}/suggest-priority")
async def suggest_task_priority(
    task_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Suggest task priority based on:
    - Task urgency
    - Dependencies
    - Project timeline
    - Business impact
    - Resource availability
    """
    try:
        ai_service = get_ai_service(db)
        return await ai_service.suggest_task_priority(task_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error suggesting task priority: {str(e)}"
        )

@router.get("/tasks/{task_id}/estimate-time")
async def estimate_task_time(
    task_id: int,
    db: Session = Depends(get_db)
) -> Dict:
    """
    Estimate task completion time based on:
    - Task complexity
    - Historical data
    - Resource availability
    - Dependencies
    - Similar tasks
    """
    try:
        ai_service = get_ai_service(db)
        return await ai_service.estimate_task_time(task_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error estimating task time: {str(e)}"
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