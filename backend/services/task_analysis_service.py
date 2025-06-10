from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from models.task import Task, TaskState
from models.user import User
from models.project import Project
from models.metrics import TaskMetrics
from schemas.task_analysis import TaskAnalysisResponse, TaskRisk, WorkloadInfo, ProjectInsight
import subprocess
import json
import pytz
from sqlalchemy import and_, or_

def get_current_time():
    """Get current time in UTC with timezone info"""
    return datetime.now(pytz.UTC)

def make_aware(dt):
    """Make a datetime timezone-aware if it isn't already"""
    if dt and dt.tzinfo is None:
        return pytz.UTC.localize(dt)
    return dt

def analyze_project_tasks(db: Session, project_id: int) -> TaskAnalysisResponse:
    """
    Enhanced analysis of project tasks using multiple data points and metrics.
    """
    # Get project and verify it exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project with id {project_id} not found")

    # Get tasks with their metrics
    tasks_with_metrics = db.query(Task, TaskMetrics).outerjoin(
        TaskMetrics, Task.id == TaskMetrics.task_id
    ).filter(Task.project_id == project_id).all()

    # Separate active and completed tasks
    active_tasks = []
    completed_tasks = []
    for task, metrics in tasks_with_metrics:
        if task.state == TaskState.DONE:
            completed_tasks.append((task, metrics))
        elif task.state != TaskState.CANCELED:
            active_tasks.append((task, metrics))

    # Calculate completion metrics
    total_tasks = len(active_tasks) + len(completed_tasks)
    completion_percentage = (len(completed_tasks) / total_tasks * 100) if total_tasks > 0 else 0

    current_time = get_current_time()

    # Enhanced risk analysis
    risk_factors = []
    for task, metrics in active_tasks:
        task_deadline = make_aware(task.deadline)
        task_start_date = make_aware(task.start_date)
        
        risk_score = 0
        risk_reasons = []

        # Deadline analysis
        if task_deadline:
            if task_deadline < current_time:
                days_overdue = (current_time - task_deadline).days
                risk_score += min(50 + days_overdue * 5, 100)
                risk_reasons.append(f"Task is overdue by {days_overdue} days")
            else:
                days_until_deadline = (task_deadline - current_time).days
                if days_until_deadline < 7:
                    risk_score += (7 - days_until_deadline) * 10
                    risk_reasons.append(f"Deadline approaching in {days_until_deadline} days")

        # Progress analysis
        expected_progress = 0
        if task_deadline and task_start_date:
            total_duration = (task_deadline - task_start_date).total_seconds()
            elapsed_duration = (current_time - task_start_date).total_seconds()
            if total_duration > 0:
                expected_progress = (elapsed_duration / total_duration) * 100

        if task.progress < expected_progress - 20:
            risk_score += 30
            risk_reasons.append(f"Progress ({task.progress}%) below expected ({expected_progress:.1f}%)")

        # Complexity analysis
        if metrics and metrics.complexity_score:
            if metrics.complexity_score > 0.7:
                risk_score += 20
                risk_reasons.append("High task complexity")

        # Dependency analysis
        if task.depends_on:
            incomplete_deps = [dep for dep in task.depends_on if dep.state != TaskState.DONE]
            if incomplete_deps:
                risk_score += 25
                risk_reasons.append(f"{len(incomplete_deps)} blocking dependencies")

        # Resource analysis
        if not task.assigned_to:
            risk_score += 40
            risk_reasons.append("No assignee")
        elif metrics and metrics.handover_count and metrics.handover_count > 2:
            risk_score += 15
            risk_reasons.append(f"Multiple handovers ({metrics.handover_count})")

        if risk_score > 30:
            risk_level = "high" if risk_score > 60 else "medium"
            risk_factors.append(TaskRisk(
                task_id=task.id,
                task_name=task.name,
                risk_type="composite",
                risk_level=risk_level,
                description="; ".join(risk_reasons),
                suggested_action=generate_mitigation_strategy(task, risk_reasons)
            ))

    # Enhanced workload analysis
    team_workload = []
    team_members = db.query(User).join(Task, Task.assigned_to == User.id).filter(
        Task.project_id == project_id,
        Task.state.notin_([TaskState.CANCELED, TaskState.DONE])
    ).distinct().all()

    for member in team_members:
        member_tasks = [(t, m) for t, m in active_tasks if t.assigned_to == member.id]
        
        # Calculate metrics
        total_complexity = sum(m.complexity_score or 0.5 for _, m in member_tasks)
        weighted_hours = sum(
            (t.planned_hours or 8) * (m.complexity_score or 0.5) 
            for t, m in member_tasks
        )
        
        overdue_tasks = sum(
            1 for t, _ in member_tasks 
            if t.deadline and make_aware(t.deadline) < current_time
        )
        
        upcoming_deadlines = sum(
            1 for t, _ in member_tasks 
            if t.deadline and current_time < make_aware(t.deadline) <= current_time + timedelta(days=7)
        )

        # Determine workload status using multiple factors
        workload_status = calculate_workload_status(
            task_count=len(member_tasks),
            weighted_hours=weighted_hours,
            total_complexity=total_complexity,
            overdue_count=overdue_tasks
        )

        team_workload.append(WorkloadInfo(
            user_id=member.id,
            user_name=member.username,
            assigned_tasks=len(member_tasks),
            total_hours=weighted_hours,
            overdue_tasks=overdue_tasks,
            upcoming_deadlines=upcoming_deadlines,
            workload_status=workload_status
        ))

    # Calculate workload distribution score
    workload_distribution_score = calculate_workload_distribution(team_workload)

    # Generate completion estimation
    estimated_completion_date, delay_probability = estimate_completion(
        project, active_tasks, completed_tasks, current_time
    )

    # Generate AI insights
    insights = generate_project_insights(
        project, active_tasks, completed_tasks, risk_factors, team_workload
    )

    # Generate recommendations
    recommendations = generate_recommendations(
        risk_factors, team_workload, workload_distribution_score, insights
    )

    return TaskAnalysisResponse(
        project_id=project_id,
        analysis_timestamp=current_time,
        completion_percentage=completion_percentage,
        total_tasks=total_tasks,
        active_tasks=len(active_tasks),
        completed_tasks=len(completed_tasks),
        overdue_tasks=sum(1 for r in risk_factors if "overdue" in r.description.lower()),
        overall_risk_level=calculate_overall_risk_level(risk_factors),
        risk_factors=risk_factors,
        team_workload=team_workload,
        workload_distribution_score=workload_distribution_score,
        estimated_completion_date=estimated_completion_date,
        delay_probability=delay_probability,
        insights=insights,
        recommendations=recommendations
    )

def calculate_workload_status(task_count: int, weighted_hours: float, 
                            total_complexity: float, overdue_count: int) -> str:
    """Calculate workload status using multiple factors"""
    score = 0
    score += task_count * 20  # Base score from task count
    score += weighted_hours * 0.5  # Hours weighted by complexity
    score += total_complexity * 10  # Direct complexity impact
    score += overdue_count * 15  # Penalty for overdue tasks

    if score > 100:
        return "overloaded"
    elif score > 60:
        return "high"
    elif score > 30:
        return "balanced"
    return "underutilized"

def calculate_workload_distribution(team_workload: List[WorkloadInfo]) -> float:
    """Calculate workload distribution score using standard deviation"""
    if not team_workload:
        return 1.0

    workloads = [w.total_hours for w in team_workload]
    avg_workload = sum(workloads) / len(workloads)
    
    if avg_workload == 0:
        return 1.0

    variance = sum((w - avg_workload) ** 2 for w in workloads) / len(workloads)
    std_dev = variance ** 0.5
    
    # Convert to a 0-1 score where 1 is perfectly distributed
    return max(0, min(1, 1 - (std_dev / avg_workload)))

def estimate_completion(project, active_tasks, completed_tasks, current_time):
    """Estimate project completion date using historical velocity"""
    if not active_tasks:
        return current_time, 0.0

    # Calculate historical velocity
    if completed_tasks:
        completed_tasks_list = [t for t, _ in completed_tasks]
        velocity = calculate_velocity(completed_tasks_list)
    else:
        velocity = 0.5  # Default velocity assumption

    # Estimate remaining work
    remaining_work = sum(
        (t.planned_hours or 8) * (1 - t.progress/100) * (m.complexity_score or 1)
        for t, m in active_tasks
    )

    if velocity <= 0:
        return project.end_date or (current_time + timedelta(days=30)), 0.9

    estimated_days = remaining_work / (velocity * 8)  # Assuming 8-hour workdays
    estimated_completion = current_time + timedelta(days=estimated_days)

    # Calculate delay probability
    if project.end_date:
        days_until_deadline = (make_aware(project.end_date) - current_time).days
        delay_probability = max(0, min(1, 1 - (days_until_deadline / estimated_days)))
    else:
        delay_probability = 0.5

    return estimated_completion, delay_probability

def calculate_velocity(completed_tasks: List[Task]) -> float:
    """Calculate team velocity based on completed tasks"""
    if not completed_tasks:
        return 0.5

    velocities = []
    for task in completed_tasks:
        if task.start_date and task.end_date:
            duration = (task.end_date - task.start_date).days or 1
            work_done = task.planned_hours or 8
            velocities.append(work_done / duration)

    return sum(velocities) / len(velocities) if velocities else 0.5

def generate_mitigation_strategy(task: Task, risk_reasons: List[str]) -> str:
    """Generate specific mitigation strategies based on risk factors"""
    strategies = []
    
    for reason in risk_reasons:
        if "overdue" in reason.lower():
            strategies.append("Review and adjust timeline")
        elif "progress" in reason.lower():
            strategies.append("Investigate blockers and allocate additional resources")
        elif "complexity" in reason.lower():
            strategies.append("Consider breaking down into smaller tasks")
        elif "dependencies" in reason.lower():
            strategies.append("Prioritize completing blocking dependencies")
        elif "no assignee" in reason.lower():
            strategies.append("Assign to team member with matching skills")
        elif "handovers" in reason.lower():
            strategies.append("Stabilize task ownership")

    return "; ".join(strategies) if strategies else "Review task and adjust resources"

def generate_project_insights(project, active_tasks, completed_tasks, 
                            risk_factors, team_workload) -> List[ProjectInsight]:
    """Generate comprehensive project insights"""
    insights = []
    
    # Analyze completion trends
    if completed_tasks:
        completion_rate = analyze_completion_trend([t for t, _ in completed_tasks])
        if completion_rate < 0.5:
            insights.append(ProjectInsight(
                insight_type="completion_trend",
                description="Project completion rate is declining",
                importance="high",
                action_required=True
            ))

    # Analyze risk distribution
    high_risks = sum(1 for r in risk_factors if r.risk_level == "high")
    if high_risks > len(active_tasks) * 0.3:
        insights.append(ProjectInsight(
            insight_type="risk_concentration",
            description=f"{high_risks} tasks ({high_risks/len(active_tasks)*100:.0f}%) are high-risk",
            importance="high",
            action_required=True
        ))

    # Analyze workload balance
    overloaded = sum(1 for w in team_workload if w.workload_status == "overloaded")
    if overloaded > 0:
        insights.append(ProjectInsight(
            insight_type="workload_imbalance",
            description=f"{overloaded} team members are overloaded",
            importance="high",
            action_required=True
        ))

    return insights

def analyze_completion_trend(completed_tasks: List[Task]) -> float:
    """Analyze the trend in task completion rate"""
    if not completed_tasks or len(completed_tasks) < 2:
        return 1.0

    # Sort by completion date
    sorted_tasks = sorted(completed_tasks, key=lambda t: t.end_date or datetime.max)
    
    # Calculate completion intervals
    intervals = []
    for i in range(1, len(sorted_tasks)):
        if sorted_tasks[i].end_date and sorted_tasks[i-1].end_date:
            interval = (sorted_tasks[i].end_date - sorted_tasks[i-1].end_date).days
            intervals.append(interval)

    if not intervals:
        return 1.0

    # Analyze trend (increasing intervals = declining rate)
    trend = sum(intervals[i] - intervals[i-1] for i in range(1, len(intervals)))
    return 1.0 if trend <= 0 else max(0.1, min(1.0, 1 - (trend / (len(intervals) * 7))))

def generate_recommendations(risk_factors: List[TaskRisk], 
                           team_workload: List[WorkloadInfo],
                           workload_distribution_score: float,
                           insights: List[ProjectInsight]) -> List[str]:
    """Generate actionable recommendations based on analysis"""
    recommendations = []

    # Risk-based recommendations
    high_risks = [r for r in risk_factors if r.risk_level == "high"]
    if high_risks:
        recommendations.append(f"Address {len(high_risks)} high-risk tasks immediately")
        risk_types = set(r.risk_type for r in high_risks)
        for risk_type in risk_types:
            if risk_type == "overdue":
                recommendations.append("Review and reprioritize overdue tasks")
            elif risk_type == "composite":
                recommendations.append("Review complex tasks for possible breakdown")

    # Workload-based recommendations
    if workload_distribution_score < 0.6:
        recommendations.append("Redistribute tasks to balance team workload")
        overloaded = [w for w in team_workload if w.workload_status == "overloaded"]
        underutilized = [w for w in team_workload if w.workload_status == "underutilized"]
        if overloaded and underutilized:
            recommendations.append(
                f"Consider moving tasks from {overloaded[0].user_name} to {underutilized[0].user_name}"
            )

    # Insight-based recommendations
    for insight in insights:
        if insight.action_required:
            if "completion rate" in insight.description:
                recommendations.append("Review and address factors slowing down completion rate")
            elif "risk concentration" in insight.description:
                recommendations.append("Conduct risk mitigation planning session")

    return list(set(recommendations))  # Remove duplicates

def calculate_overall_risk_level(risk_factors: List[TaskRisk]) -> str:
    """Calculate overall project risk level"""
    if not risk_factors:
        return "low"

    high_risks = sum(1 for r in risk_factors if r.risk_level == "high")
    medium_risks = sum(1 for r in risk_factors if r.risk_level == "medium")
    
    total_risks = len(risk_factors)
    if total_risks == 0:
        return "low"
    
    high_ratio = high_risks / total_risks
    medium_ratio = medium_risks / total_risks
    
    if high_ratio > 0.3:
        return "high"
    elif high_ratio > 0.1 or medium_ratio > 0.3:
        return "medium"
    return "low"

def _build_analysis_prompt(project: Project, tasks: List[Dict[str, Any]]) -> str:
    """
    Build a prompt for the AI model to analyze tasks
    """
    task_lines = []
    for task in tasks:
        line = (
            f"Task #{task['id']}: '{task['name']}', "
            f"state: {task['state']}, "
            f"progress: {task['progress']}%, "
            f"priority: {task['priority']}, "
            f"deadline: {task['deadline'] or 'not set'}, "
            f"assigned to: {task['assigned_to'] or 'unassigned'}, "
            f"planned hours: {task['planned_hours']}, "
            f"complexity: {task['complexity_score']}"
        )
        task_lines.append(line)

    return f"""
Analyze the following project tasks and provide insights:

Project: {project.name}
Start Date: {project.start_date}
End Date: {project.end_date}

Tasks:
{chr(10).join(task_lines)}

Please analyze and provide:
1. Overall project completion status and timeline estimation
2. Tasks at risk (overdue, unassigned, blocked, etc.)
3. Workload distribution analysis
4. Key insights and recommendations
5. Risk assessment (low/medium/high) with reasoning

Format the response as JSON with the following structure:
{{
    "completion_status": {{
        "percentage": float,
        "estimated_completion_date": "YYYY-MM-DD",
        "delay_probability": float
    }},
    "risks": [
        {{
            "task_id": int,
            "risk_type": str,
            "level": str,
            "description": str,
            "suggestion": str
        }}
    ],
    "workload": {{
        "distribution_score": float,
        "issues": [str],
        "recommendations": [str]
    }},
    "insights": [
        {{
            "type": str,
            "description": str,
            "importance": str,
            "action_required": bool
        }}
    ],
    "overall_risk_level": str,
    "recommendations": [str]
}}
"""

def _get_ai_analysis(prompt: str) -> Dict[str, Any]:
    """
    Send the prompt to Ollama and get AI analysis
    """
    try:
        result = subprocess.run(
            ["ollama", "run", "llama2", prompt],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Extract JSON from the response
        response_text = result.stdout
        # Find the JSON part (assuming it's between the first { and last })
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            raise ValueError("No valid JSON found in AI response")
            
    except subprocess.CalledProcessError as e:
        print(f"Error calling Ollama: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error parsing AI response: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

def _process_ai_response(
    db: Session,
    project_id: int,
    tasks: List[Task],
    ai_response: Dict[str, Any]
) -> TaskAnalysisResponse:
    """
    Process the AI response and create a structured analysis response
    """
    # Create risk factors
    risk_factors = [
        TaskRisk(
            task_id=risk["task_id"],
            task_name=next((t.name for t in tasks if t.id == risk["task_id"]), "Unknown"),
            risk_type=risk["risk_type"],
            risk_level=risk["level"],
            description=risk["description"],
            suggested_action=risk.get("suggestion")
        )
        for risk in ai_response.get("risks", [])
    ]

    # Calculate workload info
    workload_info = []
    users_with_tasks = db.query(User).join(Task, Task.assigned_to == User.id)\
        .filter(Task.project_id == project_id).distinct().all()
    
    for user in users_with_tasks:
        user_tasks = [t for t in tasks if t.assigned_to == user.id]
        overdue_tasks = sum(1 for t in user_tasks if t.deadline and t.deadline < datetime.now())
        upcoming_tasks = sum(1 for t in user_tasks 
                           if t.deadline and t.deadline > datetime.now() 
                           and t.deadline <= datetime.now() + timedelta(days=7))
        
        workload_info.append(WorkloadInfo(
            user_id=user.id,
            user_name=user.name,
            assigned_tasks=len(user_tasks),
            total_hours=sum(t.planned_hours or 0 for t in user_tasks),
            overdue_tasks=overdue_tasks,
            upcoming_deadlines=upcoming_tasks,
            workload_status=_determine_workload_status(len(user_tasks), overdue_tasks)
        ))

    # Create insights
    insights = [
        ProjectInsight(
            insight_type=insight["type"],
            description=insight["description"],
            importance=insight["importance"],
            action_required=insight["action_required"]
        )
        for insight in ai_response.get("insights", [])
    ]

    # Calculate completion metrics
    completed_tasks = sum(1 for t in tasks if t.state == "done")
    active_tasks = sum(1 for t in tasks if t.is_active)
    overdue_tasks = sum(1 for t in tasks 
                       if t.deadline and t.deadline < datetime.now() 
                       and t.state != "done")

    # Create final response
    return TaskAnalysisResponse(
        project_id=project_id,
        analysis_timestamp=datetime.now(),
        completion_percentage=ai_response["completion_status"]["percentage"],
        total_tasks=len(tasks),
        active_tasks=active_tasks,
        completed_tasks=completed_tasks,
        overdue_tasks=overdue_tasks,
        overall_risk_level=ai_response["overall_risk_level"],
        risk_factors=risk_factors,
        team_workload=workload_info,
        workload_distribution_score=ai_response["workload"]["distribution_score"],
        estimated_completion_date=datetime.fromisoformat(
            ai_response["completion_status"]["estimated_completion_date"]
        ) if ai_response["completion_status"].get("estimated_completion_date") else None,
        delay_probability=ai_response["completion_status"]["delay_probability"],
        insights=insights,
        recommendations=ai_response.get("recommendations", [])
    )

def _determine_workload_status(task_count: int, overdue_count: int) -> str:
    """
    Determine workload status based on task count and overdue tasks
    """
    if task_count <= 2:
        return "underutilized"
    elif task_count <= 5 and overdue_count <= 1:
        return "balanced"
    else:
        return "overloaded" 