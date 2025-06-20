from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from typing import Dict, List
from datetime import datetime, timedelta
import statistics
import hashlib
import json
import redis
import os
from fastapi.responses import JSONResponse

from database import get_db
from services.ai_service import get_ai_service
from models.task import Task, TaskState
from models.task_risk import TaskRisk
from services.ollama_client import get_ollama_client
from routers.auth import get_current_user

router = APIRouter(
    prefix="/ai",
    tags=["AI Analysis"]
)

# Simple in-memory cache (in production, use Redis)
_risk_score_cache = {}

# Setup Redis connection (simple, for demo; in production, use config/env vars)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)

def get_cache_key(user_id: int, task_ids: List[int]) -> str:
    """Generate cache key based on user_id and task_ids"""
    task_ids_str = ",".join(map(str, sorted(task_ids)))
    return f"risk_score_{user_id}_{hashlib.md5(task_ids_str.encode()).hexdigest()}"

def get_cached_risk_score(cache_key: str) -> Dict:
    """Get cached risk score if available and not expired"""
    if cache_key in _risk_score_cache:
        cached_data, timestamp = _risk_score_cache[cache_key]
        # Cache for 10 minutes
        if datetime.utcnow() - timestamp < timedelta(minutes=10):
            return cached_data
        else:
            del _risk_score_cache[cache_key]
    return None

def set_cached_risk_score(cache_key: str, data: Dict):
    """Cache risk score data with timestamp"""
    _risk_score_cache[cache_key] = (data, datetime.utcnow())

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

@router.get("/user/{user_id}/risk")
async def get_user_risk_level(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Calculate the overall risk level for a user based on all tasks assigned to them.
    - For admins/superusers: can specify any user_id.
    - For regular users: can only access their own risk level.
    - Aggregates risk levels of all assigned tasks.
    - If >30% of tasks are high risk, user risk is 'high'.
    - Else if >30% are medium, user risk is 'medium'.
    - Else, user risk is 'low'.
    - If no tasks, risk is 'low'.
    """
    # Only allow non-admins to access their own risk
    if not current_user.get("is_superuser") and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's risk level.")

    # Get all tasks assigned to the user
    tasks = db.query(Task).filter(Task.assigned_to == user_id).all()
    if not tasks:
        return {
            "user_id": user_id,
            "risk_level": "low",
            "task_risk_counts": {"high": 0, "medium": 0, "low": 0},
            "total_tasks": 0
        }

    # Import or get the AI service
    ai_service = get_ai_service(db)

    # For each task, get its risk level
    risk_counts = {"high": 0, "medium": 0, "low": 0}
    for task in tasks:
        try:
            analysis = await ai_service.analyze_task_risk(task.id)
            risk_level = analysis.get("risk_level", "low")
            if risk_level not in risk_counts:
                risk_level = "low"
            risk_counts[risk_level] += 1
        except Exception:
            # If risk analysis fails, count as low risk
            risk_counts["low"] += 1

    total_tasks = sum(risk_counts.values())
    high_pct = risk_counts["high"] / total_tasks if total_tasks else 0
    med_pct = risk_counts["medium"] / total_tasks if total_tasks else 0

    if high_pct > 0.3:
        user_risk = "high"
    elif med_pct > 0.3:
        user_risk = "medium"
    else:
        user_risk = "low"

    return {
        "user_id": user_id,
        "risk_level": user_risk,
        "task_risk_counts": risk_counts,
        "total_tasks": total_tasks
    }

def extract_risk_level(ai_explanation: str) -> str:
    """
    Extract risk level from AI explanation.
    Expected format: "Risk Level: [Level] - [explanation]"
    """
    try:
        if "Risk Level:" in ai_explanation:
            # Extract the part after "Risk Level:" and before the dash
            parts = ai_explanation.split("Risk Level:")[1].strip()
            risk_level = parts.split("-")[0].strip()
            return risk_level
        else:
            # Fallback: try to find risk level keywords
            risk_levels = ["Very Low", "Low", "Medium", "High", "Critical"]
            for level in risk_levels:
                if level in ai_explanation:
                    return level
            return "Unknown"
    except:
        return "Unknown"

@router.get("/user/{user_id}/risk-score")
async def get_user_risk_score(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Calculate the average risk score for tasks and generate an AI explanation.
    - Only active tasks (not done/cancelled) are considered.
    - For each task, collects the risk_score using the same logic as /ai/task/{task_id}/risk.
    - Returns average, min, max, median risk scores, task count, and an AI-generated explanation.
    - If the current user is a superuser/admin AND requesting their own risk score, they get global analysis.
    - If the current user is a regular user, they can only access their own risk score.
    - Adds a 'scope' field: 'user' or 'global'.
    - Results are cached for 10 minutes to improve performance.
    """
    # Only allow non-admins to access their own risk
    if not current_user.get("is_superuser") and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's risk score.")

    from models.task import Task, TaskState
    
    # If user is admin/superuser AND requesting their own risk score, show global analysis
    if current_user.get("is_superuser") and current_user["id"] == user_id:
        tasks = db.query(Task).filter(Task.state.notin_([TaskState.DONE, TaskState.CANCELED])).all()
        scope = "global"
        user_id_value = None
    else:
        # Regular users see their own tasks, or admins see specific user's tasks
        tasks = db.query(Task).filter(
            Task.assigned_to == user_id,
            Task.state.notin_([TaskState.DONE, TaskState.CANCELED])
        ).all()
        scope = "user"
        user_id_value = user_id

    if not tasks:
        return {
            "scope": scope,
            "user_id": user_id_value,
            "average_risk_score": 0,
            "min_risk_score": 0,
            "max_risk_score": 0,
            "median_risk_score": 0,
            "task_count": 0,
            "risk_level": "Very Low",
            "ai_explanation": "There are no active tasks assigned. The risk level is minimal."
        }

    # Check cache first
    task_ids = [task.id for task in tasks]
    cache_key = get_cache_key(user_id, task_ids)
    cached_result = get_cached_risk_score(cache_key)
    
    if cached_result:
        return cached_result

    from services.ai_service import get_ai_service
    ai_service = get_ai_service(db)

    risk_scores = []
    for task in tasks:
        try:
            analysis = await ai_service.analyze_task_risk(task.id)
            risk_score = analysis.get("risk_score", 0)
            risk_scores.append(risk_score)
        except Exception:
            risk_scores.append(0)

    avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
    min_risk = min(risk_scores) if risk_scores else 0
    max_risk = max(risk_scores) if risk_scores else 0
    median_risk = statistics.median(risk_scores) if risk_scores else 0
    task_count = len(risk_scores)

    # Count high and critical risk tasks
    high_risk_task_count = sum(1 for score in risk_scores if 61 <= score <= 80)
    critical_risk_task_count = sum(1 for score in risk_scores if score > 80)

    # Calculate risk level in backend
    if avg_risk <= 20:
        risk_level = "Very Low Risk"
    elif avg_risk <= 40:
        risk_level = "Low Risk"
    elif avg_risk <= 60:
        risk_level = "Medium Risk"
    elif avg_risk <= 80:
        risk_level = "High Risk"
    else:
        risk_level = "Critical Risk"

    # Pass the risk level to the AI for explanation
    if scope == "global":
        prompt = (
            f"The average risk score is {avg_risk:.1f} (scale 0-100), which is categorized as '{risk_level}'. "
            f"There are {task_count} active tasks (min: {min_risk:.1f}, max: {max_risk:.1f}, median: {median_risk:.1f}). "
            f"Explain what this means for the organization and what actions should be taken. "
            f"Format: 'Risk Level: {risk_level} - [Brief explanation]'"
        )
    else:
        prompt = (
            f"The average risk score is {avg_risk:.1f} (scale 0-100), which is categorized as '{risk_level}'. "
            f"There are {task_count} active tasks (min: {min_risk:.1f}, max: {max_risk:.1f}, median: {median_risk:.1f}). "
            f"Explain what this means for the user and what actions should be taken. "
            f"Format: 'Risk Level: {risk_level} - [Brief explanation]'"
        )

    try:
        client = get_ollama_client()
        response = await client.generate(
            model="mistral",
            prompt=prompt,
            max_tokens=120,
            temperature=0.3
        )
        ai_explanation = response.text.strip() if response and hasattr(response, 'text') else "No AI explanation available."
    except Exception as e:
        ai_explanation = f"AI explanation unavailable: {str(e)}"

    # Fallback explanation if AI fails
    if "No AI explanation available" in ai_explanation or "AI explanation unavailable" in ai_explanation:
        if avg_risk <= 20:
            ai_explanation = f"Risk Level: Very Low Risk - Your overall risk level is very low. Keep up the excellent work!"
        elif avg_risk <= 40:
            ai_explanation = f"Risk Level: Low Risk - Your overall risk level is low. Continue monitoring your tasks."
        elif avg_risk <= 60:
            ai_explanation = f"Risk Level: Medium Risk - Your overall risk level is moderate. Pay attention to tasks with higher risk scores."
        elif avg_risk <= 80:
            ai_explanation = f"Risk Level: High Risk - Your overall risk level is high. Immediate attention is needed on your riskiest tasks."
        else:
            ai_explanation = f"Risk Level: Critical Risk - Your overall risk level is critical. Urgent action is required on multiple high-risk tasks."

    # Use backend-calculated risk level
    result = {
        "scope": scope,
        "user_id": user_id_value,
        "average_risk_score": round(avg_risk, 2),
        "min_risk_score": round(min_risk, 2),
        "max_risk_score": round(max_risk, 2),
        "median_risk_score": round(median_risk, 2),
        "task_count": task_count,
        "risk_level": risk_level,
        "ai_explanation": ai_explanation,
        "high_risk_task_count": high_risk_task_count,
        "critical_risk_task_count": critical_risk_task_count
    }

    # Cache the result
    set_cached_risk_score(cache_key, result)
    # Store in Redis list for history
    try:
        redis_client.lpush(f"risk_score_history:{user_id}", json.dumps(result, default=str))
    except Exception as e:
        print(f"Error storing risk score history in Redis: {e}")
    return result

@router.get("/user/{user_id}/risk-score/history")
async def get_user_risk_score_history(user_id: int):
    """
    Fetch all historical risk score results for a user from Redis.
    Returns a list of risk score results (most recent first).
    """
    try:
        records = redis_client.lrange(f"risk_score_history:{user_id}", 0, -1)
        return [json.loads(r) for r in records]
    except Exception as e:
        print(f"Error fetching risk score history from Redis: {e}")
        return []

@router.get("/user/{user_id}/risk-score/latest")
async def get_user_latest_risk_score(user_id: int):
    """
    Fetch the latest risk score result for a user from Redis.
    Returns the most recent risk score result or None if not found.
    """
    try:
        record = redis_client.lindex(f"risk_score_history:{user_id}", 0)
        return json.loads(record) if record else None
    except Exception as e:
        print(f"Error fetching latest risk score from Redis: {e}")
        return None

@router.get("/user/{user_id}/top-risk-tasks")
async def get_top_risk_tasks(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get the top 3 active tasks with the highest risk scores for a user (or globally for admin).
    Returns a list of up to 3 tasks, sorted by risk score descending, with detailed info.
    Each task includes project name, assignee details, complexity score, due date, allocated time, and stage info.
    """
    # Only allow non-admins to access their own risk
    if not current_user.get("is_superuser") and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this user's top risk tasks.")

    from models.task import Task, TaskState
    
    # If user is admin/superuser AND requesting their own risk score, show global analysis
    if current_user.get("is_superuser") and current_user["id"] == user_id:
        tasks = db.query(Task).filter(Task.state.notin_([TaskState.DONE, TaskState.CANCELED])).all()
    else:
        # Regular users see their own tasks, or admins see specific user's tasks
        tasks = db.query(Task).filter(
            Task.assigned_to == user_id,
            Task.state.notin_([TaskState.DONE, TaskState.CANCELED])
        ).all()

    if not tasks:
        return []

    from services.ai_service import get_ai_service
    ai_service = get_ai_service(db)

    task_risk_details = []
    for task in tasks:
        try:
            analysis = await ai_service.analyze_task_risk(task.id)
            risk_score = analysis.get("risk_score", 0)
            complexity_score = analysis.get("complexity_score", getattr(task, "complexity_score", 0))
        except Exception:
            risk_score = 0
            complexity_score = getattr(task, "complexity_score", 0)
        # Project name
        project_name = None
        try:
            if hasattr(task, "project") and task.project:
                project_name = task.project.name
        except Exception:
            project_name = None
        # Assignee details
        assignee_info = None
        try:
            if hasattr(task, "assignee") and task.assignee:
                assignee_info = {
                    "id": getattr(task.assignee, "id", None),
                    "full_name": getattr(task.assignee, "full_name", None) or getattr(task.assignee, "username", None),
                    "job_title": getattr(task.assignee, "job_title", None),
                    "is_active": getattr(task.assignee, "is_active", None)
                }
        except Exception:
            assignee_info = None
        # Stage info
        stage_name = None
        stage_number = None
        total_stages = None
        try:
            if hasattr(task, "stage") and task.stage:
                stage_name = getattr(task.stage, "name", None)
                # Find stage number and total stages for the project
                if hasattr(task, "project") and task.project and hasattr(task.project, "stages"):
                    stages = list(task.project.stages)
                    total_stages = len(stages)
                    for idx, s in enumerate(stages, 1):
                        if s.id == task.stage_id:
                            stage_number = idx
                            break
        except Exception:
            stage_name = None
            stage_number = None
            total_stages = None
        # Last 3 comments
        comments_list = []
        try:
            if hasattr(task, "comments") and task.comments:
                sorted_comments = sorted(task.comments, key=lambda c: getattr(c, "created_at", None) or 0, reverse=True)
                for comment in sorted_comments[:3]:
                    user_info = None
                    try:
                        if hasattr(comment, "user") and comment.user:
                            user_info = {
                                "id": getattr(comment.user, "id", None),
                                "full_name": getattr(comment.user, "full_name", None) or getattr(comment.user, "username", None),
                                "profile_image_url": getattr(comment.user, "profile_image_url", None)
                            }
                    except Exception:
                        user_info = None
                    comments_list.append({
                        "id": comment.id,
                        "content": comment.content,
                        "created_at": comment.created_at,
                        "user": user_info
                    })
        except Exception:
            comments_list = []
        task_risk_details.append({
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "deadline": task.deadline,
            "due_date": task.deadline,
            "state": task.state,
            "priority": task.priority,
            "risk_score": risk_score,
            "complexity_score": complexity_score,
            "allocated_time": getattr(task, "planned_hours", None),
            "project_id": getattr(task, "project_id", None),
            "project_name": project_name,
            "assigned_to": getattr(task, "assigned_to", None),
            "assignee": assignee_info,
            "progress": getattr(task, "progress", None),
            "created_at": getattr(task, "created_at", None),
            "updated_at": getattr(task, "updated_at", None),
            "stage": {
                "name": stage_name,
                "number": stage_number,
                "total": total_stages
            },
            "comments": comments_list
        })

    # Sort by risk_score descending and take top 3
    top_tasks = sorted(task_risk_details, key=lambda x: x["risk_score"], reverse=True)[:3]

    # Store results in Redis (history and latest)
    timestamp = datetime.utcnow().isoformat()
    history_key = f"top_risk_tasks:{user_id}:{timestamp}"
    latest_key = f"top_risk_tasks:{user_id}:latest"
    redis_client.set(history_key, json.dumps(top_tasks, default=str))
    redis_client.set(latest_key, json.dumps(top_tasks, default=str))

    return top_tasks

@router.get("/user/{user_id}/top-risk-tasks/history")
async def get_top_risk_tasks_history(
    user_id: int
):
    """
    Fetch all historical top-risk-tasks records for a user from Redis.
    """
    pattern = f"top_risk_tasks:{user_id}:*"
    keys = [k for k in redis_client.keys(pattern) if not k.endswith(":latest")]
    history = []
    for k in sorted(keys):
        try:
            record = redis_client.get(k)
            if record:
                history.append({"timestamp": k.split(":")[-1], "tasks": json.loads(record)})
        except Exception:
            continue
    return history

@router.post("/ai/analyze-tasks")
async def analyze_tasks_with_ai(
    user_id: int = Query(..., description="User ID to analyze tasks for"),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetches all top-risk task history for the user from Redis, analyzes each task with the AI, and returns the results with ai_insight fields.
    Stores each result in Redis for later retrieval.
    """
    # Only allow non-admins to access their own analysis
    if not current_user.get("is_superuser") and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized.")

    # Fetch history from Redis
    pattern = f"top_risk_tasks:{user_id}:*"
    keys = [k for k in redis_client.keys(pattern) if not k.endswith(":latest")]
    if not keys:
        raise HTTPException(status_code=404, detail="No top-risk task history found for this user.")

    all_tasks = []
    for k in sorted(keys):
        record = redis_client.get(k)
        if record:
            all_tasks.extend(json.loads(record))

    # Analyze each task with AI
    try:
        client = get_ollama_client()
    except Exception as e:
        print(f"Error getting Ollama client: {e}")
        client = None
    analyzed = []
    for task in all_tasks:
        is_self = current_user.get("id") == task.get("assigned_to")
        is_superuser = current_user.get("is_superuser", False)
        assignee_name = None
        if task.get("assignee") and isinstance(task["assignee"], dict):
            assignee_name = task["assignee"].get("full_name", "the assignee")
        else:
            assignee_name = "the assignee"

        if is_superuser and not is_self:
            prompt = f"""
Given the following task data:
{json.dumps(task, default=str)}
You are an admin/manager. Analyze this task and provide:
- Root Cause of Risk (one sentence)
- Predicted Impact (one sentence)
- Suggested Action (one sentence, addressed to the manager about {assignee_name})
Format your response as:
Root Cause of Risk: ...\nPredicted Impact: ...\nSuggested Action: ...
"""
        else:
            prompt = f"""
Given the following task data:
{json.dumps(task, default=str)}
You are the person assigned to this task. Analyze this task and provide:
- Root Cause of Risk (one sentence)
- Predicted Impact (one sentence)
- Suggested Action (one sentence, addressed directly to you)
Format your response as:
Root Cause of Risk: ...\nPredicted Impact: ...\nSuggested Action: ...
"""
        ai_insight = ""
        ai_insights = {"root_cause": "", "predicted_impact": "", "suggested_action": ""}
        if client:
            try:
                response = await client.generate(
                    model="mistral",
                    prompt=prompt,
                    max_tokens=180,
                    temperature=0.3
                )
                ai_insight = response.text.strip() if response and hasattr(response, 'text') else ""
                if not ai_insight:
                    print(f"Empty AI insight for task {task.get('id')}, raw response: {response}")
                # Parse the AI insight into structured fields
                import re
                root_cause_match = re.search(r"Root Cause of Risk:\s*(.*?)(?:\n|$)", ai_insight, re.IGNORECASE)
                predicted_impact_match = re.search(r"Predicted Impact:\s*(.*?)(?:\n|$)", ai_insight, re.IGNORECASE)
                suggested_action_match = re.search(r"Suggested Action:\s*(.*?)(?:\n|$)", ai_insight, re.IGNORECASE)
                if root_cause_match:
                    ai_insights["root_cause"] = root_cause_match.group(1).strip()
                if predicted_impact_match:
                    ai_insights["predicted_impact"] = predicted_impact_match.group(1).strip()
                if suggested_action_match:
                    ai_insights["suggested_action"] = suggested_action_match.group(1).strip()
            except Exception as e:
                print(f"AI error for task {task.get('id')}: {e}")
                ai_insight = ""
        else:
            print("Ollama client not available, skipping AI analysis.")
        task_with_insight = dict(task)
        task_with_insight["ai_insight"] = ai_insight
        task_with_insight["ai_insights"] = ai_insights
        analyzed.append(task_with_insight)
        # Store each analysis in Redis for history (by task)
        try:
            redis_client.lpush(f"task_ai_insight_history:{task_with_insight['id']}", json.dumps(task_with_insight, default=str))
        except Exception as e:
            print(f"Error storing AI insight for task {task_with_insight['id']} in Redis: {e}")
    return analyzed

@router.get("/ai/analyze-tasks/history")
async def get_analyze_tasks_history(
    user_id: int = Query(..., description="User ID to fetch task AI analysis for"),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch the latest AI analysis for all tasks for a user (superusers: all tasks, regular users: only their tasks).
    Before returning, trigger a new analysis so the next fetch is always up-to-date.
    Returns a list of dicts with task name, assignee, and AI insight (split into root_cause, predicted_impact, suggested_action).
    """
    # Trigger a new analysis in the background (don't await)
    import asyncio
    asyncio.create_task(analyze_tasks_with_ai(user_id=user_id, current_user=current_user))

    from models.task import Task, TaskState
    db = next(get_db())
    if current_user.get("is_superuser"):
        tasks = db.query(Task).filter(Task.state.notin_([TaskState.DONE, TaskState.CANCELED])).all()
    else:
        tasks = db.query(Task).filter(
            Task.assigned_to == user_id,
            Task.state.notin_([TaskState.DONE, TaskState.CANCELED])
        ).all()
    results = []
    for task in tasks:
        try:
            record = redis_client.lindex(f"task_ai_insight_history:{task.id}", 0)
            if record:
                analysis = json.loads(record)
                ai_insights = analysis.get("ai_insights", {})
                results.append({
                    "task_id": task.id,
                    "task_name": task.name,
                    "assigned_to": analysis.get("assignee", {}).get("full_name") if analysis.get("assignee") else None,
                    "ai_insights": ai_insights
                })
        except Exception as e:
            print(f"Error fetching AI insight for task {task.id} from Redis: {e}")
    return results 