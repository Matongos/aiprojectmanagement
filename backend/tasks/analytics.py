from celery import Celery
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
import logging
from typing import Dict, Any, List
import json
import redis

from database import get_db
from models.task import Task
from models.task_risk import TaskRisk
from crud.task_risk import TaskRiskCRUD

logger = logging.getLogger(__name__)

# Import the Celery app
from celery_app import celery_app
from sqlalchemy.orm import sessionmaker
from database import engine
from models.user import User
from models.task import Task
import requests

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

redis_client = redis.Redis(host='localhost', port=6379, db=0)

@celery_app.task(bind=True)
def calculate_active_tasks_risks_task(self, user_id: int, is_superuser: bool, detailed: bool = True):
    """
    Celery task to calculate active tasks with risks analysis.
    
    Args:
        user_id: ID of the requesting user
        is_superuser: Whether the user is a superuser
        detailed: Whether to return detailed analysis (True) or summary (False)
    """
    try:
        # Create database session
        db = next(get_db())
        
        # Get active task states
        active_states = ['in_progress', 'approved', 'changes_requested']
        
        # Query active tasks based on user permissions
        if is_superuser:
            # Superusers see all active tasks
            active_tasks = db.query(Task).filter(
                Task.state.in_(active_states)
            ).all()
        else:
            # General users see only their assigned tasks
            active_tasks = db.query(Task).filter(
                Task.state.in_(active_states),
                Task.assigned_to == user_id
            ).all()
        
        task_risk_crud = TaskRiskCRUD(db)
        active_tasks_with_risks = []
        
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
                
                if detailed:
                    # Detailed analysis for /active-risks endpoint
                    task_data = _process_detailed_risk_analysis(
                        task, latest_risk, risk_factors, recommendations, metrics
                    )
                else:
                    # Summary analysis for /active-risks-summary endpoint
                    task_data = _process_summary_risk_analysis(
                        task, latest_risk, risk_factors, recommendations, metrics
                    )
                
                active_tasks_with_risks.append(task_data)
        
        # Sort by risk score (highest to lowest)
        active_tasks_with_risks.sort(key=lambda x: x['risk_score'], reverse=True)
        
        # Calculate summary statistics
        summary_stats = _calculate_summary_statistics(active_tasks_with_risks, is_superuser)
        
        result = {
            "status": "success",
            "summary": summary_stats,
            "tasks": active_tasks_with_risks,
            "user_permissions": {
                "is_superuser": is_superuser,
                "view_scope": "all_tasks" if is_superuser else "assigned_tasks_only"
            },
            "task_id": self.request.id,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Successfully processed {len(active_tasks_with_risks)} tasks for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error in calculate_active_tasks_risks_task: {str(e)}")
        raise
    finally:
        db.close()

def _process_detailed_risk_analysis(task, latest_risk, risk_factors, recommendations, metrics):
    """Process detailed risk analysis for a task."""
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
    return {
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
        }
    }

def _process_summary_risk_analysis(task, latest_risk, risk_factors, recommendations, metrics):
    """Process summary risk analysis for a task."""
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
    
    return task_risk_summary

def _calculate_summary_statistics(active_tasks_with_risks, is_superuser):
    """Calculate summary statistics for the tasks."""
    if active_tasks_with_risks:
        risk_scores = [task['risk_score'] for task in active_tasks_with_risks]
        risk_levels = [task['risk_level'] for task in active_tasks_with_risks]
        
        # Collect all AI insights and problems
        all_ai_insights = []
        all_specific_problems = []
        for task in active_tasks_with_risks:
            all_ai_insights.extend(task.get('ai_insights', []))
            all_specific_problems.extend(task.get('specific_problems', []))
        
        return {
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
            "common_problems": list(set(all_specific_problems))[:5],  # Top 5 common problems
            "user_view_type": "all_tasks" if is_superuser else "assigned_tasks_only"
        }
    else:
        return {
            "total_active_tasks": 0,
            "average_risk_score": 0,
            "highest_risk_score": 0,
            "lowest_risk_score": 0,
            "risk_distribution": {
                "extreme": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "minimal": 0
            },
            "tasks_needing_immediate_attention": 0,
            "tasks_with_high_risk": 0,
            "total_ai_insights": 0,
            "total_specific_problems": 0,
            "critical_insights": [],
            "common_problems": [],
            "user_view_type": "all_tasks" if is_superuser else "assigned_tasks_only"
        }

@celery_app.task(bind=True)
def refresh_task_risks_task(self, task_ids: List[int] = None, force_refresh: bool = False):
    """
    Celery task to refresh risk analysis for tasks to ensure data is always up to date.
    
    Args:
        task_ids: List of specific task IDs to refresh. If None, refreshes all active tasks.
        force_refresh: Whether to force refresh even if recent analysis exists
    """
    try:
        from tasks.task_risk import calculate_task_risk_analysis_task
        
        # Create database session
        db = next(get_db())
        
        if task_ids:
            # Refresh specific tasks
            tasks_to_refresh = db.query(Task).filter(Task.id.in_(task_ids)).all()
        else:
            # Refresh all active tasks
            active_states = ['in_progress', 'approved', 'changes_requested']
            tasks_to_refresh = db.query(Task).filter(Task.state.in_(active_states)).all()
        
        refreshed_count = 0
        skipped_count = 0
        
        for task in tasks_to_refresh:
            # Check if risk analysis needs refresh
            if not force_refresh:
                latest_risk = task_risk_crud.get_latest_risk_analysis(task.id)
                if latest_risk:
                    # Check if analysis is recent (within last 2 hours)
                    time_diff = datetime.now(timezone.utc) - latest_risk.created_at
                    if time_diff.total_seconds() < 7200:  # 2 hours
                        skipped_count += 1
                        continue
            
            # Trigger risk analysis refresh
            try:
                calculate_task_risk_analysis_task.delay(task.id)
                refreshed_count += 1
                logger.info(f"Queued risk refresh for task {task.id}")
            except Exception as e:
                logger.error(f"Failed to queue risk refresh for task {task.id}: {str(e)}")
        
        result = {
            "status": "success",
            "refreshed_tasks": refreshed_count,
            "skipped_tasks": skipped_count,
            "total_tasks": len(tasks_to_refresh),
            "task_id": self.request.id,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Risk refresh completed: {refreshed_count} refreshed, {skipped_count} skipped")
        return result
        
    except Exception as e:
        logger.error(f"Error in refresh_task_risks_task: {str(e)}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True)
def schedule_periodic_risk_refresh_task(self):
    """
    Scheduled Celery task to periodically refresh risk analysis for all active tasks.
    This should be run every 2 hours to ensure risk data is always fresh.
    """
    try:
        # Refresh all active tasks
        return refresh_task_risks_task.delay(force_refresh=False)
        
    except Exception as e:
        logger.error(f"Error in schedule_periodic_risk_refresh_task: {str(e)}")
        raise

@celery_app.task(bind=True)
def refresh_high_risk_tasks_task(self):
    """
    Celery task to refresh risk analysis for high-risk tasks more frequently.
    This should be run every 30 minutes for tasks with high risk scores.
    """
    try:
        # Create database session
        db = next(get_db())
        
        # Get high-risk tasks (risk score >= 60)
        high_risk_tasks = db.query(Task).join(
            TaskRisk, Task.id == TaskRisk.task_id
        ).filter(
            TaskRisk.risk_score >= 60,
            Task.state.in_(['in_progress', 'approved', 'changes_requested'])
        ).all()
        
        high_risk_task_ids = [task.id for task in high_risk_tasks]
        
        if high_risk_task_ids:
            # Refresh high-risk tasks
            return refresh_task_risks_task.delay(task_ids=high_risk_task_ids, force_refresh=True)
        else:
            return {
                "status": "success",
                "message": "No high-risk tasks found to refresh",
                "task_id": self.request.id
            }
        
    except Exception as e:
        logger.error(f"Error in refresh_high_risk_tasks_task: {str(e)}")
        raise
    finally:
        db.close()

@celery_app.task(bind=True)
def generate_personalized_ai_suggestions_task(self, user_id: int, is_superuser: bool):
    """
    Celery task to generate personalized AI suggestions for the top 3 highest-risk tasks.
    
    This task:
    1. Fetches top 3 highest-risk tasks from active tasks
    2. Analyzes user context (role, skills, current workload)
    3. Provides role-specific AI suggestions
    4. Considers whether user is assignee, manager, or superuser
    
    Args:
        user_id: ID of the requesting user
        is_superuser: Whether the user is a superuser
    """
    try:
        # Create database session
        db = next(get_db())
        
        # Import models here to avoid circular imports
        from models.user import User
        from models.task import Task
        from models.project import Project, ProjectMember, ProjectRole
        from models.task_risk import TaskRisk
        from crud.task_risk import TaskRiskCRUD
        from services.ai_service import AIService
        import json
        
        # Update task state to show progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 1,
                'total': 5,
                'status': 'Starting personalized AI suggestions generation...'
            }
        )
        
        # Get user details for context
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {
                "success": False,
                "message": "User not found",
                "user_id": user_id
            }
        
        # Get active task states
        active_states = ['in_progress', 'approved', 'changes_requested']
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 2,
                'total': 5,
                'status': 'Fetching active tasks...'
            }
        )
        
        # Query active tasks based on user permissions
        if is_superuser:
            # Superusers see all active tasks
            active_tasks = db.query(Task).filter(
                Task.state.in_(active_states)
            ).all()
        else:
            # General users see only their assigned tasks
            active_tasks = db.query(Task).filter(
                Task.state.in_(active_states),
                Task.assigned_to == user_id
            ).all()
        
        task_risk_crud = TaskRiskCRUD(db)
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 3,
                'total': 5,
                'status': 'Analyzing task risks...'
            }
        )
        
        # Get risk analysis for all active tasks
        tasks_with_risks = []
        for task in active_tasks:
            latest_risk = task_risk_crud.get_latest_risk_analysis(task.id)
            if latest_risk:
                tasks_with_risks.append({
                    "task": task,
                    "risk_analysis": latest_risk
                })
        
        # Sort by risk score and get top 3
        tasks_with_risks.sort(key=lambda x: x["risk_analysis"].risk_score, reverse=True)
        top_3_risky_tasks = tasks_with_risks[:3]
        
        if not top_3_risky_tasks:
            return {
                "success": True,
                "status": "success",
                "message": "No high-risk tasks found",
                "user_context": {
                    "user_id": user.id,
                    "user_name": user.full_name,
                    "role": "superuser" if is_superuser else "user",
                    "is_superuser": is_superuser
                },
                "suggestions": [],
                "task_id": self.request.id,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
        
        # Get user's current workload and context
        user_assigned_tasks = db.query(Task).filter(
            Task.assigned_to == user.id,
            Task.state.in_(active_states)
        ).all()
        
        user_managed_projects = []
        if is_superuser:
            # Superusers manage all projects
            user_managed_projects = db.query(Project).all()
        else:
            # Get projects where user is a member with manager role
            user_managed_projects = db.query(Project).join(
                ProjectMember, Project.id == ProjectMember.project_id
            ).filter(
                ProjectMember.user_id == user.id,
                ProjectMember.role == ProjectRole.MANAGER
            ).all()
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 4,
                'total': 5,
                'status': 'Preparing user context...'
            }
        )
        
        # Prepare user context for AI
        user_context = {
            "user_id": user.id,
            "user_name": user.full_name,
            "email": user.email,
            "role": "superuser" if is_superuser else "user",
            "is_superuser": is_superuser,
            "current_workload": len(user_assigned_tasks),
            "managed_projects": len(user_managed_projects),
            "assigned_tasks": [
                {
                    "id": task.id,
                    "name": task.name,
                    "state": task.state,
                    "progress": task.progress,
                    "deadline": task.deadline.isoformat() if task.deadline else None
                } for task in user_assigned_tasks
            ]
        }
        
        # Prepare task context for AI
        task_contexts = []
        for task_data in top_3_risky_tasks:
            task = task_data["task"]
            risk = task_data["risk_analysis"]
            
            # Determine user's relationship to this task
            user_relationship = "viewer"
            if task.assigned_to == user.id:
                user_relationship = "assignee"
            elif is_superuser:
                user_relationship = "admin"
            elif any(project.id == task.project_id for project in user_managed_projects):
                user_relationship = "manager"
            
            task_context = {
                "task_id": task.id,
                "task_name": task.name,
                "project_name": task.project.name if task.project else "Unknown",
                "assignee_name": task.assignee.full_name if task.assignee else "Unassigned",
                "state": task.state,
                "progress": task.progress or 0.0,
                "deadline": task.deadline.isoformat() if task.deadline else None,
                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "time_sensitivity": risk.time_sensitivity,
                "complexity": risk.complexity,
                "priority": risk.priority,
                "risk_factors": risk.risk_factors or {},
                "recommendations": risk.recommendations or {},
                "metrics": risk.metrics or {},
                "user_relationship": user_relationship,
                "is_assigned_to_user": task.assigned_to == user.id
            }
            task_contexts.append(task_context)
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 5,
                'total': 5,
                'status': 'Generating AI suggestions...'
            }
        )
        
        # Generate AI suggestions using AIService
        try:
            from services.ai_service import AIService
            import requests
            
            # Create AI service instance
            ai_service = AIService(db)
            
            # Create comprehensive prompt with complete risk analysis
            prompt = f"""You are an AI project management assistant providing personalized recommendations.

USER CONTEXT:
- User: {user_context['user_name']} (ID: {user_context['user_id']})
- Role: {user_context['role']} {'(SUPERUSER - can manage all tasks)' if user_context['is_superuser'] else '(Regular user - limited to assigned tasks)'}
- Current Workload: {user_context['current_workload']} assigned tasks
- Managed Projects: {user_context['managed_projects']} projects
- User Type: {'SUPERUSER - Has full access to all tasks and projects' if user_context['is_superuser'] else 'REGULAR USER - Limited to assigned tasks only'}

TOP 3 HIGHEST-RISK TASKS WITH ESSENTIAL RISK ANALYSIS:

{chr(10).join([f'''
TASK {i+1}: {task['task_name']}
- Project: {task['project_name']}
- Assignee: {task['assignee_name']}
- User's Relationship: {task['user_relationship']} {'(ASSIGNED TO USER)' if task['is_assigned_to_user'] else ''}
- Risk Score: {task['risk_score']} ({task['risk_level']})
- Progress: {task['progress']}%
- Deadline: {task['deadline']}
- State: {task['state']}

ESSENTIAL RISK COMPONENTS:
- Time Sensitivity Score: {task['time_sensitivity']}
- Complexity Score: {task['complexity']}
- Priority Score: {task['priority']}

TOP RISK FACTORS:
{_extract_top_risk_factors(task['risk_factors'])}

KEY RECOMMENDATIONS:
{_extract_key_recommendations(task['recommendations'])}
''' for i, task in enumerate(task_contexts)])}

Based on this risk analysis, provide personalized AI suggestions for {user_context['user_name']}.

IMPORTANT CONSIDERATIONS:
1. User is a {user_context['role'].upper()} - {'can take action on any task' if user_context['is_superuser'] else 'can only act on assigned tasks'}
2. Each task has risk analysis with scores and factors
3. Provide exactly 2 specific, actionable suggestions per task

For each task, provide:
- 2 immediate actions the user can realistically take (consider their role)
- 2 strategic recommendations for the task
- Specific impact analysis based on risk factors
- Timeframe for each action

Return JSON only with this structure:
{{
  "overall_assessment": "Brief assessment of the 3 tasks",
  "user_role_analysis": "Analysis of user's role and capabilities",
  "task_suggestions": [
    {{
      "task_id": 1,
      "task_name": "Task Name",
      "risk_score": 150.0,
      "risk_level": "extreme",
      "user_relationship": "assignee",
      "immediate_actions": ["Action 1", "Action 2"],
      "strategic_recommendations": ["Strategy 1", "Strategy 2"],
      "potential_impact": "Impact analysis",
      "timeframe": "immediate"
    }}
  ],
  "overall_recommendations": ["Overall rec 1", "Overall rec 2", "Overall rec 3"],
  "next_steps": ["Step 1", "Step 2", "Step 3"],
  "final_message": "Final summary message"
}}"""

            # Generate AI response using the same pattern as working AI methods
            logger.info(f"Starting AI analysis for personalized suggestions for user {user_context['user_name']}")
            
            response = requests.post(
                ai_service.ollama_url,
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": True
                },
                timeout=120,  # Increased from 60 to 120 seconds
                stream=True
            )
            
            if response.status_code != 200:
                logger.error(f"AI service returned status {response.status_code}: {response.text}")
                raise Exception(f"AI service error: {response.status_code}")
            
            # Collect streaming response
            ai_response_text = ""
            logger.info("Receiving AI response stream:")
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        if 'response' in chunk:
                            ai_response_text += chunk['response']
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"Complete AI response: {ai_response_text}")
            
            # Parse AI response
            if ai_response_text:
                try:
                    # Try to extract JSON from the response
                    import re
                    json_match = re.search(r'\{.*\}', ai_response_text, re.DOTALL)
                    if json_match:
                        ai_suggestions = json.loads(json_match.group())
                        ai_generated = True
                        ai_model = "mistral"
                        error = None
                    else:
                        raise ValueError("No JSON found in AI response")
                except Exception as parse_error:
                    ai_suggestions = _generate_fallback_suggestions(task_contexts, user_context)
                    ai_generated = False
                    ai_model = "mistral_fallback"
                    error = f"AI parsing failed: {str(parse_error)}"
            else:
                ai_suggestions = _generate_fallback_suggestions(task_contexts, user_context)
                ai_generated = False
                ai_model = "mistral_fallback"
                error = "AI parsing failed: Empty AI response"
                
        except Exception as ai_error:
            logger.error(f"Error generating AI suggestions: {str(ai_error)}")
            ai_suggestions = _generate_fallback_suggestions(task_contexts, user_context)
            ai_generated = False
            ai_model = "mistral_fallback"
            error = f"AI generation failed: {str(ai_error)}"
        
        # Prepare top risky tasks for response
        top_risky_tasks = []
        for task_data in top_3_risky_tasks:
            task = task_data["task"]
            risk = task_data["risk_analysis"]
            
            # Determine user's relationship to this task
            user_relationship = "viewer"
            if task.assigned_to == user.id:
                user_relationship = "assignee"
            elif is_superuser:
                user_relationship = "admin"
            elif any(project.id == task.project_id for project in user_managed_projects):
                user_relationship = "manager"
            
            top_risky_tasks.append({
                "task_id": task.id,
                "task_name": task.name,
                "project_name": task.project.name if task.project else "Unknown",
                "assignee_name": task.assignee.full_name if task.assignee else "Unassigned",
                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "user_relationship": user_relationship
            })
        
        # Add error info to AI suggestions if there was an error
        if error:
            ai_suggestions["ai_generated"] = ai_generated
            ai_suggestions["ai_model"] = ai_model
            ai_suggestions["error"] = error
            logger.warning(f"Using fallback suggestions due to error: {error}")
        else:
            ai_suggestions["ai_generated"] = ai_generated
            ai_suggestions["ai_model"] = ai_model
            logger.info(f"Successfully generated AI suggestions using {ai_model}")
        
        # Store results in Redis cache for quick frontend access
        try:
            from services.redis_service import get_redis_client
            redis_client = get_redis_client()
            import copy
            # Create cache key for this user's personalized suggestions
            cache_key = f"personalized_ai_suggestions:{user_id}"
            last_key = f"personalized_ai_suggestions:last:{user_id}"
            result_key = f"personalized_ai_suggestions:result:{self.request.id}"
            # Prepare cache data (remove cache_expires_at)
            cache_data = {
                "status": "success",
                "user_context": user_context,
                "top_risky_tasks": top_risky_tasks,
                "ai_suggestions": ai_suggestions,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "task_id": self.request.id,
                "processed_at": datetime.now(timezone.utc).isoformat()
            }
            # Store in Redis with NO expiration for last_key (persists until overwritten)
            redis_client.set(last_key, json.dumps(cache_data))
            # Store in Redis with NO expiration for main key (as before)
            redis_client.set(cache_key, json.dumps(cache_data))
            # Store in Redis with NO expiration for result_key (per celery job)
            redis_client.set(result_key, json.dumps(cache_data))
            logger.info(f"Successfully cached personalized AI suggestions for user {user_id} in Redis (no expiration)")
        except Exception as cache_error:
            logger.warning(f"Failed to cache personalized AI suggestions for user {user_id}: {str(cache_error)}")
            # Continue without caching - the result will still be returned
        
        result = {
            "status": "success",
            "user_context": user_context,
            "top_risky_tasks": top_risky_tasks,
            "ai_suggestions": ai_suggestions,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "task_id": self.request.id,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Successfully generated personalized AI suggestions for user {user_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error in generate_personalized_ai_suggestions_task: {str(e)}")
        return {
            "success": False,
            "message": f"Error generating personalized AI suggestions: {str(e)}",
            "user_id": user_id,
            "task_id": self.request.id
        }
    finally:
        db.close()

def _generate_fallback_suggestions(task_contexts, user_context):
    """Generate fallback suggestions when AI fails"""
    task_suggestions = []
    
    for task in task_contexts:
        task_suggestions.append({
            "task_id": task["task_id"],
            "task_name": task["task_name"],
            "risk_score": task["risk_score"],
            "risk_level": task["risk_level"],
            "user_relationship": task["user_relationship"],
            "immediate_actions": [
                f"Review {task['task_name']} progress and timeline (Risk: {task['risk_score']})",
                f"Contact {task['assignee_name']} for status update"
            ],
            "strategic_recommendations": [
                f"Monitor {task['task_name']} closely for delays (Time Sensitivity: {task['time_sensitivity']})",
                f"Consider additional resources if needed (Complexity: {task['complexity']})"
            ],
            "potential_impact": f"High risk of delay or failure for {task['task_name']} with {task['risk_score']} risk score",
            "timeframe": "immediate"
        })
    
    return {
        "overall_assessment": f"Found {len(task_contexts)} high-risk tasks requiring immediate attention. Risk scores range from {min([t['risk_score'] for t in task_contexts])} to {max([t['risk_score'] for t in task_contexts])}.",
        "user_role_analysis": f"User {user_context['user_name']} is a {user_context['role']} with {user_context['current_workload']} current tasks",
        "task_suggestions": task_suggestions,
        "overall_recommendations": [
            "Review all high-risk tasks immediately",
            "Prioritize tasks with highest risk scores",
            "Monitor progress closely"
        ],
        "next_steps": [
            "Review task details",
            "Take immediate action",
            "Update progress"
        ],
        "final_message": "Focus on the highest risk tasks first and take immediate action."
    }


@celery_app.task(bind=True)
def trigger_ai_suggestions_for_all_users_task(self):
    """
    Celery task to trigger AI suggestions for all users.
    This task is called when a task's due date is changed to refresh
    personalized AI suggestions for all users in the system.
    """
    try:
        # Create database session
        db = next(get_db())
        
        # Import models here to avoid circular imports
        from models.user import User
        from services.user_service import get_users
        import json
        
        # Update task state to show progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 1,
                'total': 3,
                'status': 'Starting AI suggestions refresh for all users...'
            }
        )
        
        # Get all active users
        all_users = get_users(db, skip=0, limit=1000)  # Get up to 1000 users
        
        if not all_users:
            logger.info("No users found to trigger AI suggestions for")
            return {
                "success": True,
                "message": "No users found to trigger AI suggestions for",
                "users_processed": 0
            }
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 2,
                'total': 3,
                'status': f'Triggering AI suggestions for {len(all_users)} users...'
            }
        )
        
        # Trigger AI suggestions for each user
        users_processed = 0
        for user in all_users:
            try:
                # Queue AI suggestions task for this user
                generate_personalized_ai_suggestions_task.delay(
                    user_id=user["id"],
                    is_superuser=user.get("is_superuser", False)
                )
                users_processed += 1
                logger.info(f"Queued AI suggestions refresh for user {user['id']} ({user['full_name']})")
            except Exception as e:
                logger.warning(f"Failed to queue AI suggestions for user {user['id']}: {str(e)}")
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 3,
                'total': 3,
                'status': f'Completed triggering AI suggestions for {users_processed} users'
            }
        )
        
        logger.info(f"Successfully triggered AI suggestions refresh for {users_processed} users")
        return {
            "success": True,
            "message": f"Triggered AI suggestions refresh for {users_processed} users",
            "users_processed": users_processed,
            "total_users": len(all_users)
        }
        
    except Exception as e:
        logger.error(f"Error in trigger_ai_suggestions_for_all_users_task: {str(e)}")
        return {
            "success": False,
            "message": f"Error triggering AI suggestions for all users: {str(e)}"
        }
    finally:
        db.close()

def _extract_top_risk_factors(risk_factors):
    """Extract top risk factors from a dictionary"""
    if not risk_factors or not isinstance(risk_factors, dict):
        return "No risk factors available"
    
    top_factors = []
    for factor_name, factor_data in risk_factors.items():
        if isinstance(factor_data, dict):
            score = factor_data.get('score', 0)
            if score > 5:
                top_factors.append(f"{factor_name.replace('_', ' ').title()}: {score:.1f} points")
    
    if not top_factors:
        return "No high-risk factors identified"
    
    return "\n".join(top_factors[:3])  # Limit to top 3 factors

def _extract_key_recommendations(recommendations):
    """Extract key recommendations from a dictionary"""
    if not recommendations or not isinstance(recommendations, dict):
        return "No recommendations available"
    
    key_recommendations = []
    for category, actions in recommendations.items():
        if isinstance(actions, list):
            for action in actions[:2]:  # Limit to 2 actions per category
                priority = "immediate" if category == "immediate_actions" else "short_term" if category == "short_term" else "long_term"
                key_recommendations.append(f"{category.replace('_', ' ').title()} - {action} (Priority: {priority})")
    
    if not key_recommendations:
        return "No specific recommendations available"
    
    return "\n".join(key_recommendations[:5])  # Limit to top 5 recommendations

# Celery task for AI-driven resource allocation optimization
@celery_app.task(bind=True)
def optimize_resources_task(self, project_id):
    db = SessionLocal()
    try:
        # Fetch users
        users = db.query(User).filter(User.is_active == True).all()
        # Fetch project tasks
        project_tasks = db.query(Task).filter(
            Task.project_id == project_id,
            Task.state.in_(['in_progress', 'approved', 'changes_requested', 'to_do'])
        ).all()
        # Find unassigned tasks
        unassigned_tasks = [task for task in project_tasks if not task.assigned_to]
        # Prepare tasks data
        tasks_data = []
        for task in unassigned_tasks:
            required_skills = []
            if task.description:
                desc = task.description.lower()
                for skill in ["python", "devops", "ui/ux", "react", "sql", "docker", "aws", "design", "testing", "project management"]:
                    if skill in desc:
                        required_skills.append(skill)
            tasks_data.append({
                "id": task.id,
                "name": task.name,
                "priority": task.priority,
                "description": task.description,
                "required_skills": required_skills
            })
        # Prepare users data
        users_data = []
        for user in users:
            active_tasks = db.query(Task).filter(
                Task.assigned_to == user.id,
                Task.state.in_(['in_progress', 'approved', 'changes_requested', 'to_do'])
            ).count()
            users_data.append({
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "job_title": user.job_title,
                "profession": user.profession,
                "experience_level": user.experience_level,
                "skills": user.skills or [],
                "expertise": user.expertise or [],
                "certifications": user.certifications or [],
                "specializations": user.specializations or [],
                "roles": [role.name for role in user.roles] if user.roles else [],
                "current_workload": active_tasks,
                "availability": "available"
            })
        # Build prompt
        prompt = f"""
Role: You are an AI project resource allocator. Your job is to assign tasks to the best available team member based on:
- Skills match (required)
- Current workload (lower is better)
- Task priority (high priority takes precedence)
- Availability (no conflicts)
- Roles and expertise

Data:
{{
  "users": {users_data},
  "tasks": {tasks_data}
}}

Task: Assign each task to the best user. Return JSON in this format:
{{
  "task_analysis": [{{"task_id": int, "inferred_skills": list}}],
  "assignments": [{{"task_id": int, "assigned_to": int, "reason": str}}]
}}
"""
        ollama_payload = {
            "model": "mistral",
            "prompt": prompt,
            "format": "json",
            "stream": False
        }
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=ollama_payload,
            timeout=120
        )
        response.raise_for_status()
        ai_result = response.json()
        ai_response = ai_result.get("response")
        try:
            parsed = json.loads(ai_response)
            # Build user_id to name mapping
            user_id_to_name = {user.id: user.full_name or user.username for user in users}
            # Add assigned_to_name to each assignment
            if "assignments" in parsed:
                for assignment in parsed["assignments"]:
                    best_user_id = assignment.get("assigned_to")
                    assignment["assigned_to_name"] = user_id_to_name.get(best_user_id, "Unknown")
            # Store in Redis for 1 hour
            redis_key = f"ai_assignment_suggestion:project:{project_id}"
            redis_client.set(redis_key, json.dumps(parsed), ex=3600)
            return parsed
        except Exception:
            # Store raw result if parsing fails
            redis_key = f"ai_assignment_suggestion:project:{project_id}"
            redis_client.set(redis_key, json.dumps(ai_result), ex=3600)
            return ai_result
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return {"error": str(e), "traceback": tb}
    finally:
        db.close() 