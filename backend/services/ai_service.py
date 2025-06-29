from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timezone, timedelta
import json
from zoneinfo import ZoneInfo
import logging
import requests
import traceback

from services.ollama_service import get_ollama_client
from services.vector_service import VectorService
from services.weather_service import get_weather_service
from services.redis_service import get_redis_client
from models.task import Task
from models.project import Project, ProjectMember
from models.time_entry import TimeEntry
from models.user import User
from models.activity import Activity
from schemas.task import TaskState
from services.complexity_service import ComplexityService
from models.task_risk import TaskRisk
from models.comment import Comment
from models.metrics import TaskMetrics
from crud.task_risk import TaskRiskCRUD

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.ollama_client = get_ollama_client()
        self.vector_service = VectorService(db)
        self.weather_service = get_weather_service()
        self.ollama_url = "http://localhost:11434/api/generate"
        self.redis_client = get_redis_client()
        
    def _get_current_time(self) -> datetime:
        """Get current time with UTC timezone"""
        return datetime.now(timezone.utc)

    def _ensure_tz_aware(self, dt: Optional[datetime]) -> Optional[datetime]:
        """Ensure datetime is timezone aware"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
        
    def get_cached_time_risk(self, task_id: int) -> Optional[Dict]:
        """
        Retrieve cached time risk data for a task from Redis.
        Returns None if not found or if Redis is unavailable.
        """
        try:
            cache_key = f"task_time_risk:{task_id}"
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data and "cache_info" in cached_data:
                # Check if cache is still valid
                next_update = datetime.fromisoformat(cached_data["cache_info"]["next_update"])
                if datetime.now(timezone.utc) < next_update:
                    return cached_data
                else:
                    # Cache expired, return None to trigger recalculation
                    return None
            
            return cached_data
        except Exception as e:
            logger.warning(f"Error retrieving cached time risk for task {task_id}: {str(e)}")
            return None

    def get_time_risk_cache_status(self, task_id: int) -> Dict:
        """
        Get information about the time risk cache status for a task.
        """
        try:
            cache_key = f"task_time_risk:{task_id}"
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                next_update = datetime.fromisoformat(cached_data["cache_info"]["next_update"])
                time_until_update = (next_update - datetime.now(timezone.utc)).total_seconds()
                
                return {
                    "is_cached": True,
                    "cache_expires_in_seconds": max(0, int(time_until_update)),
                    "next_update": cached_data["cache_info"]["next_update"],
                    "update_frequency": cached_data["cache_info"]["update_frequency"],
                    "current_risk": cached_data["time_risk_percentage"],
                    "risk_level": cached_data["risk_level"]
                }
            else:
                return {
                    "is_cached": False,
                    "message": "No cached data found - calculation needed"
                }
                
        except Exception as e:
            logger.warning(f"Error checking cache status for task {task_id}: {str(e)}")
            return {
                "is_cached": False,
                "error": str(e)
            }

    def store_time_risk_cache(self, task_id: int, time_risk_data: Dict, expiration_seconds: int = 3600) -> bool:
        """
        Store time risk data in Redis cache.
        Returns True if successful, False otherwise.
        """
        try:
            cache_key = f"task_time_risk:{task_id}"
            return self.redis_client.setex(cache_key, expiration_seconds, time_risk_data)
        except Exception as e:
            logger.warning(f"Error storing time risk cache for task {task_id}: {str(e)}")
            return False

    async def generate_project_insights(self, project_id: int) -> Dict:
        """Generate comprehensive project insights."""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        return {
            "project_id": project_id,
            "progress": {
                "completion_rate": 0.65,
                "on_track": True,
                "milestone_status": "On Schedule"
            },
            "performance_metrics": {
                "velocity": 85,
                "quality_score": 0.92,
                "efficiency": 0.88
            },
            "resource_utilization": {
                "overall": 0.75,
                "by_team": {
                    "frontend": 0.8,
                    "backend": 0.7,
                    "qa": 0.75
                }
            },
            "bottlenecks": [
                {
                    "type": "Resource Constraint",
                    "description": "Limited backend developers",
                    "impact": "HIGH"
                }
            ],
            "success_patterns": [
                "Regular code reviews",
                "Daily standups",
                "Automated testing"
            ],
            "improvement_areas": [
                "Documentation coverage",
                "Sprint planning accuracy"
            ],
            "team_dynamics": {
                "collaboration_score": 0.85,
                "communication_effectiveness": 0.8,
                "knowledge_sharing": 0.75
            }
        }
    
    async def analyze_project_risks(self, project_id: int) -> Dict:
        """
        Comprehensive project risk analysis that considers all tasks and project-level factors.
        """
        # Get project and its tasks
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        tasks = self.db.query(Task).filter(Task.project_id == project_id).all()
        if not tasks:
            return {
                "risk_level": 1,
                "risk_factors": ["No tasks found in project"],
                "mitigations": ["Add tasks to the project to begin risk analysis"],
                "timeline_status": "unknown",
                "resource_recommendations": ["Project requires task planning"]
            }

        try:
            # 1. Analyze all tasks individually
            task_analyses = []
            for task in tasks:
                try:
                    analysis = await self.analyze_task_risk(task.id)
                    task_analyses.append(analysis)
                except Exception as e:
                    print(f"Error analyzing task {task.id}: {str(e)}")
                    continue

            if not task_analyses:
                return {
                    "risk_level": 5,
                    "risk_factors": ["Unable to analyze tasks"],
                    "mitigations": ["Review task data and retry analysis"],
                    "timeline_status": "unknown",
                    "resource_recommendations": ["Verify task data integrity"]
                }

            # 2. Calculate project-wide metrics
            total_risk_score = sum(a.get("risk_score", 0) for a in task_analyses)
            avg_risk_score = total_risk_score / len(task_analyses)
            risk_level = int(min(10, max(1, avg_risk_score * 10)))

            # 3. Aggregate task issues
            critical_tasks = []
            role_mismatches = []
            dependency_issues = []
            timeline_issues = []
            workload_issues = []
            total_estimated_delay = 0

            for task, analysis in zip(tasks, task_analyses):
                # Track critical tasks
                if analysis.get("risk_score", 0) > 0.7:
                    critical_tasks.append({
                        "task_id": task.id,
                        "name": task.name,
                        "risk_score": analysis.get("risk_score"),
                        "factors": analysis.get("risk_factors", [])
                    })

                # Track role mismatches
                role_match = analysis.get("metrics", {}).get("role_match", {})
                if role_match and role_match.get("risk_level") == "high":
                    role_mismatches.append({
                        "task_id": task.id,
                        "name": task.name,
                        "reason": role_match.get("reason")
                    })

                # Track dependencies
                deps = analysis.get("metrics", {}).get("dependencies", {})
                if deps and deps.get("blocked"):
                    dependency_issues.append({
                        "task_id": task.id,
                        "name": task.name,
                        "blockers": deps.get("blocking_tasks", [])
                    })

                # Track timeline issues
                time_metrics = analysis.get("metrics", {}).get("time", {})
                if time_metrics and (time_metrics.get("is_overdue") or time_metrics.get("deadline_approaching")):
                    timeline_issues.append({
                        "task_id": task.id,
                        "name": task.name,
                        "overdue_days": time_metrics.get("overdue_days", 0),
                        "days_to_deadline": time_metrics.get("days_to_deadline")
                    })

                # Track workload
                workload = analysis.get("metrics", {}).get("workload", {})
                if workload and workload.get("overloaded"):
                    workload_issues.append({
                        "task_id": task.id,
                        "name": task.name,
                        "assignee": task.assignee.username if task.assignee else None,
                        "active_tasks": workload.get("active_tasks", 0)
                    })

                # Accumulate delays
                total_estimated_delay += analysis.get("estimated_delay_days", 0)

            # 4. Generate risk factors
            risk_factors = []
            
            if critical_tasks:
                risk_factors.append(f"{len(critical_tasks)} high-risk tasks requiring immediate attention")
            if role_mismatches:
                risk_factors.append(f"{len(role_mismatches)} tasks have role-skill mismatches")
            if dependency_issues:
                risk_factors.append(f"{len(dependency_issues)} tasks blocked by dependencies")
            if timeline_issues:
                risk_factors.append(f"{len(timeline_issues)} tasks have timeline issues")
            if workload_issues:
                risk_factors.append(f"{len(workload_issues)} instances of resource overallocation")
            if total_estimated_delay > 0:
                risk_factors.append(f"Potential project delay of {total_estimated_delay} days")

            # 5. Generate mitigation strategies
            mitigations = []
            
            if critical_tasks:
                mitigations.append("Conduct immediate review of high-risk tasks")
                mitigations.append("Implement risk mitigation plans for critical tasks")
            if role_mismatches:
                mitigations.append("Review and reallocate tasks based on skill-role alignment")
                mitigations.append("Consider team training for skill gaps")
            if dependency_issues:
                mitigations.append("Schedule dependency resolution workshop")
                mitigations.append("Create action plan for blocked tasks")
            if timeline_issues:
                mitigations.append("Review and adjust project timeline")
                mitigations.append("Consider timeline recovery options")
            if workload_issues:
                mitigations.append("Redistribute workload among team members")
                mitigations.append("Review resource allocation strategy")

            # 6. Determine timeline status
            if len(timeline_issues) > len(tasks) * 0.3:
                timeline_status = "critical"
            elif len(timeline_issues) > len(tasks) * 0.1:
                timeline_status = "at_risk"
            else:
                timeline_status = "on_track"

            # 7. Generate resource recommendations
            resource_recommendations = []
            
            if workload_issues:
                resource_recommendations.append(f"Add resources to {len(workload_issues)} overloaded areas")
            if role_mismatches:
                resource_recommendations.append("Review team composition and skill distribution")
            if total_estimated_delay > 30:
                resource_recommendations.append("Consider additional resources to recover timeline")
            if dependency_issues:
                resource_recommendations.append("Allocate resources to resolve dependency bottlenecks")

            # 8. Return comprehensive analysis
            return {
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "mitigations": mitigations,
                "timeline_status": timeline_status,
                "resource_recommendations": resource_recommendations,
                "detailed_metrics": {
                    "critical_tasks": critical_tasks,
                    "role_mismatches": role_mismatches,
                    "dependency_issues": dependency_issues,
                    "timeline_issues": timeline_issues,
                    "workload_issues": workload_issues,
                    "total_tasks": len(tasks),
                    "analyzed_tasks": len(task_analyses),
                    "average_risk_score": round(avg_risk_score, 2),
                    "estimated_total_delay": total_estimated_delay,
                    "task_distribution": {
                        "high_risk": len(critical_tasks),
                        "role_mismatch": len(role_mismatches),
                        "blocked": len(dependency_issues),
                        "timeline_issues": len(timeline_issues),
                        "workload_issues": len(workload_issues)
                    }
                }
            }

        except Exception as e:
            print(f"Error in project risk analysis: {str(e)}")
            return {
                "risk_level": 5,
                "risk_factors": ["Error in risk analysis"],
                "mitigations": ["Review project data and retry"],
                "timeline_status": "unknown",
                "resource_recommendations": ["Verify project data"]
            } 

    async def analyze_task_risk(self, task_id: int) -> Dict:
        """Fetch all data required for task risk analysis without performing analysis."""
        # Get task with all necessary relationships
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        try:
            # 1. Get project details
            project = self.db.query(Project).filter(Project.id == task.project_id).first()
            
            # 2. Get task complexity data
            complexity_service = ComplexityService()
            complexity_analysis = await complexity_service.analyze_task_complexity(self.db, task_id)
            
            # 3. Get detailed assignee data
            assignee_data = None
            assignee_active_tasks = []
            if task.assigned_to:
                assignee = self.db.query(User).filter(User.id == task.assigned_to).first()
                if assignee:
                    # Get assignee's active tasks
                    assignee_active_tasks = self.db.query(Task).filter(
                        Task.assigned_to == assignee.id,
                        Task.state.in_(['in_progress', 'changes_requested', 'approved']),
                        Task.id != task_id  # Exclude current task
                    ).all()
                    
                    assignee_data = {
                        'id': assignee.id,
                        'username': assignee.username,
                        'full_name': assignee.full_name,
                        'job_title': assignee.job_title,
                        'profession': assignee.profession,
                        'expertise': assignee.expertise or [],
                        'skills': assignee.skills or [],
                        'experience_level': assignee.experience_level,
                        'active_tasks_count': len(assignee_active_tasks),
                        'active_tasks': [
                            {
                                'id': t.id,
                                'name': t.name,
                                'description': t.description,
                                'state': t.state,
                                'progress': t.progress,
                                'deadline': t.deadline.isoformat() if t.deadline else None
                            } for t in assignee_active_tasks
                        ]
                    }

            # 4. Get task comments
            task_comments = self.db.query(Comment).filter(
                Comment.task_id == task_id
            ).order_by(Comment.created_at.desc()).all()
            
            comments_data = [
                {
                    'id': comment.id,
                    'content': comment.content,
                    'created_by': comment.created_by,
                    'created_at': comment.created_at.isoformat(),
                    'author_name': comment.author.full_name if comment.author else 'Unknown'
                } for comment in task_comments
            ]

            # 5. Get project comments (for dependency analysis context)
            project_comments = self.db.query(Comment).filter(
                Comment.project_id == task.project_id,
                Comment.task_id.is_(None)  # Only project-level comments
            ).order_by(Comment.created_at.desc()).all()
            
            project_comments_data = [
                {
                    'id': comment.id,
                    'content': comment.content,
                    'created_by': comment.created_by,
                    'created_at': comment.created_at.isoformat(),
                    'author_name': comment.author.full_name if comment.author else 'Unknown'
                } for comment in project_comments
            ]

            # 6. Get all tasks in the project for dependency analysis
            project_tasks = self.db.query(Task).filter(
                Task.project_id == task.project_id,
                Task.id != task_id  # Exclude current task
            ).all()
            
            project_tasks_data = [
                {
                    'id': t.id,
                    'name': t.name,
                    'description': t.description,
                    'state': t.state,
                    'progress': t.progress,
                    'deadline': t.deadline.isoformat() if t.deadline else None,
                    'assigned_to': t.assigned_to,
                    'created_at': t.created_at.isoformat()
                } for t in project_tasks
            ]

            # 7. Calculate time-related data
            current_time = self._get_current_time()
            task_deadline = self._ensure_tz_aware(task.deadline)
            task_start_date = self._ensure_tz_aware(task.start_date)
            
            time_data = {
                'current_time': current_time.isoformat(),
                'task_created_at': self._ensure_tz_aware(task.created_at).isoformat(),
                'task_start_date': task_start_date.isoformat() if task_start_date else None,
                'task_deadline': task_deadline.isoformat() if task_deadline else None,
                'planned_hours': task.planned_hours or 0,
                'progress': task.progress or 0,
                'days_to_deadline': None,
                'is_overdue': False,
                'overdue_days': 0
            }
            
            if task_deadline:
                if task_deadline < current_time:
                    time_data['is_overdue'] = True
                    time_data['overdue_days'] = (current_time - task_deadline).days
                    time_data['days_to_deadline'] = -(current_time - task_deadline).days
                else:
                    time_data['days_to_deadline'] = (task_deadline - current_time).days

            # 8. Determine if task is outdoor/indoor
            weather_service = get_weather_service()
            is_outdoor_task = weather_service.is_outdoor_task(task.description or '', task.name)
            task_environment = "outdoor" if is_outdoor_task else "indoor"

            # 9. Get task dependencies
            task_dependencies = [
                {
                    'id': dep.id,
                    'name': dep.name,
                    'description': dep.description,
                    'state': dep.state,
                    'progress': dep.progress
                } for dep in task.depends_on
            ]

            # 10. Get dependent tasks (tasks that depend on this task)
            dependent_tasks = [
                {
                    'id': dep.id,
                    'name': dep.name,
                    'description': dep.description,
                    'state': dep.state,
                    'progress': dep.progress
                } for dep in task.dependent_tasks
            ]

            # 11. Get task metrics if available
            task_metrics = self.db.query(TaskMetrics).filter(TaskMetrics.task_id == task_id).first()
            metrics_data = None
            if task_metrics:
                metrics_data = {
                    'actual_duration': task_metrics.actual_duration,
                    'time_estimate_accuracy': task_metrics.time_estimate_accuracy,
                    'complexity_score': task_metrics.complexity_score,
                    'dependency_count': task_metrics.dependency_count,
                    'comment_count': task_metrics.comment_count,
                    'handover_count': task_metrics.handover_count
                }

            # 12. Get cached time risk data or calculate if not available
            time_risk_data = None
            try:
                cached_time_risk = self.get_cached_time_risk(task_id)
                if cached_time_risk:
                    # Weight the time risk against 30 (every 100% = 30 points)
                    time_risk_percentage = cached_time_risk.get('time_risk_percentage', 0)
                    weighted_risk_score = (time_risk_percentage / 100) * 30
                    
                    time_risk_data = {
                        "cached_time_risk": cached_time_risk,
                        "weighted_risk_score": round(weighted_risk_score, 2),
                        "calculation": f"({time_risk_percentage} / 100) * 30 = {weighted_risk_score}",
                        "risk_level": cached_time_risk.get('risk_level', 'unknown'),
                        "time_data": cached_time_risk.get('time_data', {}),
                        "cache_status": "valid"
                    }
                else:
                    # No cache found - calculate time risk on-demand
                    logger.info(f"No cached time risk found for task {task_id}, calculating on-demand...")
                    calculated_time_risk = await self._analyze_time_risks(task)
                    
                    if calculated_time_risk:
                        # Weight the calculated time risk against 30
                        time_risk_percentage = calculated_time_risk.get('time_risk_percentage', 0)
                        weighted_risk_score = (time_risk_percentage / 100) * 30
                        
                        # Store the calculated result in cache for future use
                        self.store_time_risk_cache(task_id, calculated_time_risk, expiration_seconds=3600)
                        
                        time_risk_data = {
                            "cached_time_risk": calculated_time_risk,
                            "weighted_risk_score": round(weighted_risk_score, 2),
                            "calculation": f"({time_risk_percentage} / 100) * 30 = {weighted_risk_score}",
                            "risk_level": calculated_time_risk.get('risk_level', 'unknown'),
                            "time_data": calculated_time_risk.get('time_data', {}),
                            "cache_status": "calculated_and_cached"
                        }
                    else:
                        # Fallback if calculation fails
                        time_risk_data = {
                            "cached_time_risk": None,
                            "weighted_risk_score": 15.0,  # Default medium risk (50% of 30)
                            "calculation": "Calculation failed, using default medium risk",
                            "risk_level": "medium",
                            "time_data": {},
                            "cache_status": "calculation_failed"
                        }
            except Exception as e:
                logger.error(f"Error in time risk analysis for task {task_id}: {str(e)}")
                time_risk_data = {
                    "cached_time_risk": None,
                    "weighted_risk_score": 15.0,  # Default medium risk (50% of 30)
                    "calculation": f"Error in time risk analysis: {str(e)}",
                    "risk_level": "medium",
                    "time_data": {},
                    "cache_status": "error"
                }

            # 13. Perform AI analysis for role/person match (out of 20 points)
            role_match_analysis = None
            try:
                role_match_analysis = await self._analyze_role_task_match_ai(
                task_name=task.name,
                    task_description=task.description or "",
                    assignee_data=assignee_data,
                    active_tasks_count=len(assignee_active_tasks),
                    active_tasks=assignee_data['active_tasks'] if assignee_data else []
                )
            except Exception as e:
                role_match_analysis = {
                    "ai_analysis_performed": False,
                    "error": str(e),
                    "role_match_score": 0,
                    "workload_score": 0,
                    "total_score": 0,
                    "analysis_details": "AI analysis failed"
                }

            # 14. Perform AI analysis for comments (out of 10 points)
            comments_analysis = None
            try:
                comments_analysis = await self._analyze_comments_ai(
                    task_comments=comments_data,
                    project_comments=project_comments_data,
                    task_name=task.name,
                    task_deadline=task.deadline,
                    current_time=current_time
                )
            except Exception as e:
                comments_analysis = {
                    "ai_analysis_performed": False,
                    "error": str(e),
                    "communication_score": 5,  # Default medium risk
                    "analysis_details": "AI analysis failed"
                }

            # 15. Perform AI analysis for task dependencies (out of 10 points)
            dependency_analysis = None
            try:
                logger.info(f"Starting dependency analysis for task {task.name} with {len(project_tasks_data)} project tasks")
                
                dependency_analysis = await self._analyze_task_dependencies_ai(
                    current_task={
                        'id': task.id,
                        'name': task.name,
                        'description': task.description or ""
                    },
                    project_tasks=project_tasks_data,
                    project_context={
                        'project_name': project.name,
                        'project_description': project.description or "",
                        'total_project_tasks': len(project_tasks_data)
                    }
                )
                
                logger.info(f"Dependency analysis completed: {dependency_analysis}")
                
            except Exception as e:
                logger.error(f"Error in dependency analysis for task {task.id}: {str(e)}")
                dependency_analysis = {
                    "ai_analysis_performed": False,
                    "error": str(e),
                    "dependency_score": 0.0,  # Default no dependency risk
                    "analysis_details": f"AI dependency analysis failed: {str(e)}",
                    "risk_level": "low",
                    "dependent_tasks": [],
                    "total_dependent_tasks": 0,
                    "critical_dependencies": 0,
                    "dependency_impact": "low",
                    "blocking_potential": "low",
                    "recommendations": ["Manual dependency review recommended"],
                    "overall_assessment": "Unable to assess dependencies due to analysis failure",
                    "project_tasks_analyzed": len(project_tasks_data)
                }

            # Return all collected data without analysis
            return {
                "task_id": task_id,
                "data_collection_timestamp": current_time.isoformat(),
                "analysis_performed": True,  # Now we're doing AI analysis
                "collected_data": {
                    # 1. Task dueness (20% weight later)
                    "task_dueness": {
                        "days_to_deadline": time_data['days_to_deadline'],
                        "is_overdue": time_data['is_overdue'],
                        "overdue_days": time_data['overdue_days'],
                        "deadline": time_data['task_deadline'],
                        "start_date": time_data['task_start_date'],
                        "created_at": time_data['task_created_at']
                    },
                    
                    # 2. Task complexity (20% weight later)
                    "task_complexity": {
                        "complexity_score": complexity_analysis.total_score,
                        "complexity_factors": complexity_analysis.factors.__dict__,
                        "environment_type": complexity_analysis.environment_type.value,
                        "weather_impact": complexity_analysis.weather_impact.__dict__ if complexity_analysis.weather_impact else None
                    },
                    
                    # 3. Assigned person analysis (20% weight - AI analyzed)
                    "assigned_person": {
                        "assignee_data": assignee_data,
                        "active_tasks_count": len(assignee_active_tasks),
                        "active_tasks": assignee_data['active_tasks'] if assignee_data else [],
                        "ai_analysis": role_match_analysis,
                        "role_match_score": role_match_analysis.get('role_match_score', 0) if role_match_analysis else 0,
                        "workload_score": role_match_analysis.get('workload_score', 0) if role_match_analysis else 0,
                        "total_score": role_match_analysis.get('total_score', 0) if role_match_analysis else 0
                    },
                    
                    # 4. Task dependency analysis (10% weight later)
                    "task_dependencies": {
                        "current_task": {
                            'id': task.id,
                            'name': task.name,
                            'description': task.description,
                            'project_id': task.project_id
                        },
                        "project_context": {
                            'project_name': project.name,
                            'project_description': project.description,
                            'total_project_tasks': len(project_tasks_data)
                        },
                        "dependencies": task_dependencies,
                        "dependent_tasks": dependent_tasks,
                        "all_project_tasks": project_tasks_data,
                        "ai_analysis": dependency_analysis,
                        "dependency_score": dependency_analysis.get('dependency_score', 0.0) if dependency_analysis else 0.0,
                        "dependency_risk_level": dependency_analysis.get('risk_level', 'low') if dependency_analysis else 'low',
                        "dependency_analysis_needed": False  # Now done by AI
                    },
                    
                    # 5. Comments analysis (10% weight later)
                    "comments_analysis": comments_analysis,
                    
                    # 6. Task environment (10% weight later)
                    "task_environment": {
                        "is_outdoor": is_outdoor_task,
                        "environment_type": task_environment,
                        "weather_impact_analysis_needed": is_outdoor_task  # Only if outdoor task
                    },
                    
                    # 7. Time risk analysis (weighted against 30)
                    "time_risk_analysis": time_risk_data,
                    
                    # Additional context data
                    "task_details": {
                        "name": task.name,
                        "description": task.description,
                        "state": task.state,
                        "priority": task.priority,
                        "progress": task.progress,
                        "planned_hours": task.planned_hours,
                        "created_at": task.created_at.isoformat(),
                        "updated_at": task.updated_at.isoformat() if task.updated_at else None
                    },
                    
                    "project_details": {
                        "id": project.id,
                        "name": project.name,
                        "description": project.description,
                        "start_date": project.start_date.isoformat() if project.start_date else None,
                        "end_date": project.end_date.isoformat() if project.end_date else None,
                        "progress": project.progress
                    },
                    
                    "metrics": metrics_data
                }
            }

        except Exception as e:
            print(f"Error in analyze_task_risk: {str(e)}")
            raise ValueError(f"Error analyzing task risk: {str(e)}")

    def _store_risk_analysis(self, task_id: int, analysis: Dict) -> None:
        """Store the risk analysis results in the database"""
        try:
            # Create new TaskRisk entry
            task_risk = TaskRisk(
                task_id=task_id,
                risk_score=analysis["risk_score"],
                risk_level=analysis["risk_level"],
                time_sensitivity=analysis["risk_breakdown"]["time_sensitivity"],
                complexity=analysis["risk_breakdown"]["complexity"],
                priority=analysis["risk_breakdown"]["priority"],
                risk_factors=analysis["risk_factors"],
                recommendations=analysis["recommendations"],
                metrics=analysis["metrics"]
            )
            
            # Add and commit to database
            self.db.add(task_risk)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Error storing risk analysis: {str(e)}")
            # Don't raise the error - we want the analysis to still be returned even if storage fails

    def _calculate_priority_risk(self, task: Task) -> float:
        """Calculate risk score based on task priority (returns 0-1)"""
        priority_scores = {
            'low': 0.2,
            'normal': 0.5,
            'high': 0.8,
            'urgent': 1.0
        }
        
        # Use priority_score if available (ensure it's 0-1)
        if hasattr(task, 'priority_score') and task.priority_score is not None:
            return min(1.0, task.priority_score / 100)  # Convert from 0-100 to 0-1
        
        return priority_scores.get(task.priority.lower(), 0.5)

    async def _analyze_role_task_match_ai(
        self,
        task_name: str,
        task_description: str,
        assignee_data: Optional[Dict],
        active_tasks_count: int,
        active_tasks: List[Dict]
    ) -> Dict:
        """
        AI analysis for role/task match and workload assessment.
        Returns a score out of 20 (10 for role match + 10 for workload).
        """
        if not assignee_data:
            return {
                "ai_analysis_performed": True,
                "role_match_score": 10,  # Maximum risk - no role match possible
                "workload_score": 10,    # Maximum risk - no workload assessment possible
                "total_score": 20,       # Maximum risk - unassigned task
                "analysis_details": {
                    "role_match_reasoning": "No assignee - task is unassigned (maximum risk)",
                    "workload_reasoning": "No assignee - cannot assess workload (maximum risk)",
                    "risk_level": "extreme",
                    "skill_gaps": ["No assignee identified"],
                    "workload_concerns": ["Task is unassigned"]
                },
                "risk_level": "extreme",
                "recommendations": [
                    "Assign task to a team member immediately",
                    "Review task requirements and identify suitable assignee",
                    "Consider task priority and urgency"
                ]
            }

        try:
            # Prepare active tasks summary for workload analysis
            active_tasks_summary = []
            for task in active_tasks:
                active_tasks_summary.append(f"Task: {task.get('name', 'Unknown')} - {task.get('state', 'unknown')} - {task.get('progress', 0)}% complete")

            # Enhanced prompt with more specific instructions
            prompt = f"""You are an expert project manager analyzing task assignments across ALL industries and fields. Analyze the following task and assignee match.

TASK TO ANALYZE:
Name: {task_name}
Description: {task_description or 'No description provided'}

ASSIGNEE INFORMATION:
Full Name: {assignee_data.get('full_name', 'Unknown')}
Job Title: {assignee_data.get('job_title', 'Unknown')}
Profession: {assignee_data.get('profession', 'Unknown')}
Skills: {', '.join(assignee_data.get('skills', [])) if assignee_data.get('skills') else 'No skills listed'}
Expertise: {', '.join(assignee_data.get('expertise', [])) if assignee_data.get('expertise') else 'No expertise listed'}
            Experience Level: {assignee_data.get('experience_level', 'Unknown')}
            
CURRENT WORKLOAD:
Active Tasks Count: {active_tasks_count}
Active Tasks:
{chr(10).join(active_tasks_summary) if active_tasks_summary else 'No active tasks'}

ANALYSIS REQUIREMENTS:
1. Role/Task Match (Score out of 10):
   - Evaluate if the assignee's job title, skills, and expertise align with task requirements
   - Consider ALL industries: Software, Marketing, Sales, Construction, Healthcare, Education, Manufacturing, Retail, Finance, etc.
   - Score 0 = perfect match (no risk), 10 = complete mismatch (high risk)
   
   UNIVERSAL ROLE ANALYSIS PRINCIPLES:
   - Consider transferable skills across industries
   - Evaluate experience level and adaptability
   - Look for logical role progression and skill overlap
   - Consider industry-specific knowledge requirements
   
   EXAMPLES ACROSS INDUSTRIES:
   - Marketing Manager + Content Creation = 1-2/10 (perfect match)
   - Sales Rep + Customer Research = 2-3/10 (good match)
   - Construction Worker + Safety Training = 1-2/10 (perfect match)
   - Nurse + Patient Care = 1-2/10 (perfect match)
   - Teacher + Curriculum Development = 1-2/10 (perfect match)
   - Accountant + Financial Analysis = 1-2/10 (perfect match)
   - Designer + Creative Task = 1-2/10 (perfect match)
   - Developer + Technical Task = 1-2/10 (perfect match)
   
   MISMATCH EXAMPLES:
   - Accountant + Surgery = 9-10/10 (complete mismatch)
   - Teacher + Construction = 8-9/10 (poor match)
   - Sales Rep + Software Development = 8-9/10 (poor match)

2. Workload Assessment (Score out of 10):
   - Evaluate current workload based on active tasks count and task states
   - Consider if adding this task would overload the person
   - Score 0 = no workload issues (no risk), 10 = severely overloaded (high risk)
   - 0 active tasks = 0/10 (no risk), 1-2 tasks = 2-3/10 (low risk), 3+ tasks = 5-7/10 (medium risk), 5+ tasks = 8-10/10 (high risk)

You MUST return ONLY valid JSON in this exact format:
{{
    "role_match_score": 2.0,
    "workload_score": 0.0,
    "total_score": 2.0,
    "role_match_reasoning": "Job title and skills align well with task requirements for this industry",
    "workload_reasoning": "Assignee has no active tasks, can easily take on this task (no workload risk)",
    "risk_level": "low",
    "recommendations": ["Assignment looks good", "Consider providing additional training if needed"],
    "skill_gaps": [],
    "workload_concerns": []
}}"""

            logger.info(f"Sending AI analysis request for task {task_name} with assignee {assignee_data.get('full_name', 'Unknown')}")
            
            # Use streaming to see AI response as it comes
            logger.info("Starting AI analysis with streaming...")

            response = requests.post(
                self.ollama_url,
                json={
                    "model": "mistral",  # Changed from codellama to mistral
                    "prompt": prompt,
                    "stream": True  # Enable streaming to see response as it comes
                },
                timeout=60,  # Increased timeout for Mistral
                stream=True  # Enable HTTP streaming
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
                            # Log each chunk as it comes
                            logger.info(f"AI chunk: {chunk['response']}")
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"Complete AI response: {ai_response_text}")
            logger.info(f"FULL AI JSON RESPONSE: {ai_response_text}")  # Log the complete JSON response
            
            # Try to parse JSON response
            try:
                analysis = json.loads(ai_response_text)
                logger.info(f"Parsed AI analysis: {json.dumps(analysis, indent=2)}")  # Log the parsed JSON
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI JSON response: {e}")
                logger.error(f"Raw AI response: {ai_response_text}")
                # Fallback to manual analysis
                return self._fallback_role_analysis(task_name, task_description, assignee_data, active_tasks_count)
            
            # Validate required fields
            required_fields = ['role_match_score', 'workload_score', 'total_score']
            missing_fields = [field for field in required_fields if field not in analysis]
            
            if missing_fields:
                logger.warning(f"AI response missing fields: {missing_fields}")
                return self._fallback_role_analysis(task_name, task_description, assignee_data, active_tasks_count)
            
            return {
                "ai_analysis_performed": True,
                "role_match_score": round(float(analysis.get('role_match_score', 0)), 2),
                "workload_score": round(float(analysis.get('workload_score', 0)), 2),
                "total_score": round(float(analysis.get('total_score', 0)), 2),
                "analysis_details": {
                    "role_match_reasoning": analysis.get('role_match_reasoning', 'No reasoning provided'),
                    "workload_reasoning": analysis.get('workload_reasoning', 'No reasoning provided'),
                    "risk_level": analysis.get('risk_level', 'medium'),
                    "skill_gaps": analysis.get('skill_gaps', []),
                    "workload_concerns": analysis.get('workload_concerns', [])
                },
                "risk_level": analysis.get('risk_level', 'medium'),
                "recommendations": analysis.get('recommendations', [])
            }
            
        except Exception as e:
            logger.error(f"Error in AI role analysis: {str(e)}")
            return self._fallback_role_analysis(task_name, task_description, assignee_data, active_tasks_count)

    def _fallback_role_analysis(
        self,
        task_name: str,
        task_description: str,
        assignee_data: Optional[Dict],
        active_tasks_count: int
    ) -> Dict:
        """
        Fallback analysis when AI fails or provides incomplete data.
        Uses rule-based logic to provide reasonable scores.
        HIGHER SCORES = HIGHER RISK
        UNIVERSAL - Works for ALL industries and fields
        """
        try:
            # Handle unassigned tasks (maximum risk)
            if not assignee_data:
                return {
                    "ai_analysis_performed": False,
                    "role_match_score": 10,  # Maximum risk - no role match possible
                    "workload_score": 10,    # Maximum risk - no workload assessment possible
                    "total_score": 20,       # Maximum risk - unassigned task
                    "analysis_details": {
                        "role_match_reasoning": "No assignee - task is unassigned (maximum risk)",
                        "workload_reasoning": "No assignee - cannot assess workload (maximum risk)",
                        "risk_level": "extreme",
                        "skill_gaps": ["No assignee identified"],
                        "workload_concerns": ["Task is unassigned"]
                    },
                    "risk_level": "extreme",
                    "recommendations": [
                        "Assign task to a team member immediately",
                        "Review task requirements and identify suitable assignee",
                        "Consider task priority and urgency"
                    ]
                }
            
            # Rule-based role match analysis
            job_title = assignee_data.get('job_title', '').lower() if assignee_data else ''
            task_name_lower = task_name.lower()
            task_desc_lower = (task_description or '').lower()
            
            role_match_score = 5.0  # Default middle score (medium risk)
            
            # UNIVERSAL INDUSTRY ANALYSIS
            
            # Marketing & Content Tasks
            if any(word in task_name_lower or word in task_desc_lower for word in ['content', 'writing', 'text', 'copy', 'seo', 'marketing', 'social', 'campaign', 'advertising']):
                if any(word in job_title for word in ['marketing', 'content', 'writer', 'seo', 'social', 'advertising', 'communications']):
                    role_match_score = 1.0  # Perfect match (no risk)
                elif any(word in job_title for word in ['manager', 'director', 'coordinator']):
                    role_match_score = 2.0  # Good match (low risk)
                else:
                    role_match_score = 6.0  # Poor match (medium-high risk)
            
            # Sales & Customer Tasks
            elif any(word in task_name_lower or word in task_desc_lower for word in ['sales', 'customer', 'client', 'prospect', 'lead', 'pitch', 'presentation']):
                if any(word in job_title for word in ['sales', 'account', 'customer', 'client', 'business']):
                    role_match_score = 1.0  # Perfect match (no risk)
                elif any(word in job_title for word in ['manager', 'director', 'representative']):
                    role_match_score = 2.0  # Good match (low risk)
                else:
                    role_match_score = 6.0  # Poor match (medium-high risk)
            
            # Financial & Accounting Tasks
            elif any(word in task_name_lower or word in task_desc_lower for word in ['financial', 'accounting', 'budget', 'expense', 'invoice', 'tax', 'audit', 'reporting']):
                if any(word in job_title for word in ['accountant', 'financial', 'finance', 'bookkeeper', 'auditor']):
                    role_match_score = 1.0  # Perfect match (no risk)
                elif any(word in job_title for word in ['manager', 'director', 'analyst']):
                    role_match_score = 2.0  # Good match (low risk)
                else:
                    role_match_score = 7.0  # Poor match (high risk)
            
            # Healthcare & Medical Tasks
            elif any(word in task_name_lower or word in task_desc_lower for word in ['patient', 'medical', 'healthcare', 'treatment', 'care', 'nursing', 'doctor', 'clinic']):
                if any(word in job_title for word in ['nurse', 'doctor', 'medical', 'healthcare', 'patient', 'clinical']):
                    role_match_score = 1.0  # Perfect match (no risk)
                elif any(word in job_title for word in ['manager', 'director', 'coordinator']):
                    role_match_score = 3.0  # Moderate match (medium risk)
                else:
                    role_match_score = 8.0  # Poor match (high risk)
            
            # Education & Training Tasks
            elif any(word in task_name_lower or word in task_desc_lower for word in ['teaching', 'education', 'training', 'curriculum', 'lesson', 'student', 'learning']):
                if any(word in job_title for word in ['teacher', 'educator', 'trainer', 'instructor', 'professor']):
                    role_match_score = 1.0  # Perfect match (no risk)
                elif any(word in job_title for word in ['manager', 'director', 'coordinator']):
                    role_match_score = 2.0  # Good match (low risk)
                else:
                    role_match_score = 6.0  # Poor match (medium-high risk)
            
            # Construction & Manual Tasks
            elif any(word in task_name_lower or word in task_desc_lower for word in ['construction', 'building', 'repair', 'maintenance', 'installation', 'assembly', 'manual']):
                if any(word in job_title for word in ['construction', 'worker', 'technician', 'mechanic', 'installer', 'maintenance']):
                    role_match_score = 1.0  # Perfect match (no risk)
                elif any(word in job_title for word in ['supervisor', 'manager', 'foreman']):
                    role_match_score = 2.0  # Good match (low risk)
                else:
                    role_match_score = 7.0  # Poor match (high risk)
            
            # Manufacturing & Production Tasks
            elif any(word in task_name_lower or word in task_desc_lower for word in ['manufacturing', 'production', 'assembly', 'quality', 'inventory', 'warehouse', 'factory']):
                if any(word in job_title for word in ['manufacturing', 'production', 'operator', 'technician', 'quality', 'warehouse']):
                    role_match_score = 1.0  # Perfect match (no risk)
                elif any(word in job_title for word in ['supervisor', 'manager', 'coordinator']):
                    role_match_score = 2.0  # Good match (low risk)
                else:
                    role_match_score = 6.0  # Poor match (medium-high risk)
            
            # Retail & Customer Service Tasks
            elif any(word in task_name_lower or word in task_desc_lower for word in ['retail', 'customer service', 'store', 'shop', 'inventory', 'display', 'merchandise']):
                if any(word in job_title for word in ['retail', 'sales', 'customer service', 'cashier', 'clerk']):
                    role_match_score = 1.0  # Perfect match (no risk)
                elif any(word in job_title for word in ['manager', 'supervisor', 'coordinator']):
                    role_match_score = 2.0  # Good match (low risk)
                else:
                    role_match_score = 5.0  # Moderate match (medium risk)
            
            # IT & Software Development Tasks (keeping existing logic but making it more flexible)
            elif any(word in task_name_lower or word in task_desc_lower for word in ['develop', 'code', 'programming', 'software', 'system', 'database', 'api', 'website']):
                if any(word in job_title for word in ['developer', 'engineer', 'programmer', 'software', 'it', 'technical']):
                    role_match_score = 1.0  # Perfect match (no risk)
                elif any(word in job_title for word in ['manager', 'director', 'architect']):
                    role_match_score = 3.0  # Moderate match (medium risk)
                else:
                    role_match_score = 7.0  # Poor match (high risk)
            
            # Design & Creative Tasks
            elif any(word in task_name_lower or word in task_desc_lower for word in ['design', 'creative', 'art', 'graphic', 'visual', 'ui', 'ux', 'wireframe', 'mockup']):
                if any(word in job_title for word in ['designer', 'creative', 'artist', 'graphic', 'ui', 'ux']):
                    role_match_score = 1.0  # Perfect match (no risk)
                elif any(word in job_title for word in ['developer', 'manager', 'director']):
                    role_match_score = 3.0  # Moderate match (medium risk)
                else:
                    role_match_score = 6.0  # Poor match (medium-high risk)
            
            # Administrative & Management Tasks
            elif any(word in task_name_lower or word in task_desc_lower for word in ['admin', 'management', 'coordination', 'planning', 'organization', 'reporting', 'documentation']):
                if any(word in job_title for word in ['manager', 'director', 'coordinator', 'administrator', 'assistant']):
                    role_match_score = 1.0  # Perfect match (no risk)
                elif any(word in job_title for word in ['supervisor', 'lead', 'specialist']):
                    role_match_score = 2.0  # Good match (low risk)
                else:
                    role_match_score = 4.0  # Moderate match (medium risk)
            
            # Research & Analysis Tasks
            elif any(word in task_name_lower or word in task_desc_lower for word in ['research', 'analysis', 'data', 'report', 'study', 'survey', 'investigation']):
                if any(word in job_title for word in ['analyst', 'researcher', 'specialist', 'scientist']):
                    role_match_score = 1.0  # Perfect match (no risk)
                elif any(word in job_title for word in ['manager', 'director', 'coordinator']):
                    role_match_score = 2.0  # Good match (low risk)
                else:
                    role_match_score = 5.0  # Moderate match (medium risk)
            
            # Workload analysis (HIGHER SCORE = HIGHER RISK)
            if active_tasks_count == 0:
                workload_score = 0.0  # No workload (no risk)
                workload_reasoning = "No active tasks - can easily take on this task (no risk)"
            elif active_tasks_count <= 2:
                workload_score = 2.0  # Low workload (low risk)
                workload_reasoning = f"Low workload with {active_tasks_count} active tasks (low risk)"
            elif active_tasks_count <= 4:
                workload_score = 5.0  # Moderate workload (medium risk)
                workload_reasoning = f"Moderate workload with {active_tasks_count} active tasks (medium risk)"
            else:
                workload_score = 8.0  # High workload (high risk)
                workload_reasoning = f"High workload with {active_tasks_count} active tasks (high risk)"
            
            total_score = role_match_score + workload_score
            
            # Determine risk level (HIGHER SCORE = HIGHER RISK)
            if total_score <= 5:
                risk_level = "low"
            elif total_score <= 10:
                risk_level = "medium"
            else:
                risk_level = "high"
            
            # Generate recommendations
            recommendations = []
            if role_match_score > 5:
                recommendations.append("Consider reassigning to someone with more relevant skills")
            if workload_score > 5:
                recommendations.append("Consider workload distribution or timeline adjustment")
            
            logger.info(f"Fallback analysis - Role: {role_match_score}, Workload: {workload_score}, Total: {total_score}, Risk: {risk_level}")
            
            return {
                "ai_analysis_performed": False,
                "role_match_score": round(role_match_score, 2),
                "workload_score": round(workload_score, 2),
                "total_score": round(total_score, 2),
                "analysis_details": {
                    "role_match_reasoning": f"Rule-based analysis: {job_title} assigned to {task_name} (score: {role_match_score})",
                    "workload_reasoning": workload_reasoning,
                    "risk_level": risk_level,
                    "skill_gaps": [],
                    "workload_concerns": []
                },
                "risk_level": risk_level,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Error in fallback analysis: {str(e)}")
            return {
                "ai_analysis_performed": False,
                "error": str(e),
                "role_match_score": 5.0,  # Default medium risk
                "workload_score": 5.0,    # Default medium risk
                "total_score": 10.0,      # Default medium risk
                "analysis_details": f"Fallback analysis failed: {str(e)}",
                    "risk_level": "medium",
                "recommendations": ["Review task assignment manually"]
            }

    async def analyze_task_urgency(self, task_id: int, context: Dict) -> Dict:
        """
        Analyze task urgency using AI to determine relative importance and suggested order.
        Returns detailed analysis including urgency score, impact score, and reasoning.
        """
        try:
            # Prepare prompt for AI
            prompt = self._create_urgency_analysis_prompt(context)
            
            # Get AI response
            response = await self._get_ai_response(prompt)
            
            # Parse and validate response
            analysis = self._parse_urgency_analysis(response)
            
            return {
                "task_id": task_id,
                "urgency_score": analysis.get("urgency_score", 0.5),
                "impact_score": analysis.get("impact_score", 0.5),
                "reasoning": analysis.get("reasoning", []),
                "suggested_order": analysis.get("suggested_order", 0)
            }
        except Exception as e:
            logger.error(f"Error in AI task urgency analysis: {str(e)}")
            return {
                "urgency_score": 0.5,
                "impact_score": 0.5,
                "reasoning": ["Failed to get AI analysis"],
                "suggested_order": 0
            }

    def _create_urgency_analysis_prompt(self, context: Dict) -> str:
        """Create a detailed prompt for task urgency analysis"""
        deadline_str = context["deadline"].isoformat() if context["deadline"] else "No deadline"
        dependencies_str = "\n".join([f"- {dep['name']} ({dep['state']})" for dep in context["dependencies"]])
        blocking_tasks_str = "\n".join([f"- {dep['name']} ({dep['state']})" for dep in context["dependent_tasks"]])
        
        return f"""
        Analyze the following task and provide urgency scores and reasoning:

        Task Description: {context["description"]}
        Deadline: {deadline_str}
        Complexity Score: {context["complexity_score"]}
        Project Urgency: {context["project_urgency"]}
        
        Dependencies:
        {dependencies_str or "None"}
        
        Blocking Tasks:
        {blocking_tasks_str or "None"}
        
        Created: {context["created_at"]}
        Last Updated: {context["last_updated"]}
        State: {context["state"]}

        Please analyze this task and provide:
        1. Urgency score (0-1)
        2. Impact score (0-1)
        3. Reasoning for the scores
        4. Suggested processing order
        
        Consider factors like:
        - Deadline proximity
        - Number of dependent tasks
        - Task complexity
        - Project urgency
        - Dependencies status
        """

    def _parse_urgency_analysis(self, response: str) -> Dict:
        """Parse AI response into structured analysis"""
        try:
            # Add your AI response parsing logic here
            # This is a placeholder implementation
            return {
                "urgency_score": 0.8,  # Example score
                "impact_score": 0.7,    # Example score
                "reasoning": [
                    "High number of dependent tasks",
                    "Close to deadline",
                    "Critical for project progress"
                ],
                "suggested_order": 1
            }
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            return {
                "urgency_score": 0.5,
                "impact_score": 0.5,
                "reasoning": ["Failed to parse AI analysis"],
                "suggested_order": 0
            }

    async def analyze_content(
        self,
        content_type: str,
        content: Dict[str, Any],
        analysis_prompt: str
    ) -> Dict[str, Any]:
        """
        Analyze content using AI and return structured results.
        
        Args:
            content_type: Type of content being analyzed (e.g., 'task_priority')
            content: Dictionary containing the content to analyze
            analysis_prompt: Specific instructions for the analysis
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # For task priority analysis
            if content_type == "task_priority":
                return await self._analyze_task_priority(content)
            
            # Default fallback analysis
            return {
                "score": 50.0,
                "score_breakdown": {
                    "content_score": 20.0,
                    "priority_level_score": 15.0,
                    "reasoning_score": 10.0,
                    "characteristics_score": 5.0
                },
                "explanation": "Default analysis performed"
            }
            
        except Exception as e:
            logger.error(f"Error in AI content analysis: {str(e)}")
            raise

    async def _analyze_task_priority(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze task content for priority scoring.
        
        Args:
            content: Dictionary containing task information
            
        Returns:
            Dictionary containing score and breakdown
        """
        try:
            # Extract task information
            task_name = content.get("task_name", "")
            description = content.get("description", "")
            priority_level = content.get("priority_level", "normal")
            priority_reasoning = content.get("priority_reasoning", [])
            deadline = content.get("deadline")
            is_blocking = content.get("is_blocking", False)
            
            # Calculate content score (40%)
            content_score = self._calculate_content_score(task_name, description)
            
            # Calculate priority level score (30%)
            priority_score = self._calculate_priority_score(priority_level)
            
            # Calculate reasoning score (20%)
            reasoning_score = self._calculate_reasoning_score(priority_reasoning)
            
            # Calculate characteristics score (10%)
            characteristics_score = self._calculate_characteristics_score(
                deadline=deadline,
                is_blocking=is_blocking
            )
            
            # Calculate total score
            total_score = (
                content_score +
                priority_score +
                reasoning_score +
                characteristics_score
            )
            
            return {
                "score": total_score,
                "score_breakdown": {
                    "content_score": content_score,
                    "priority_level_score": priority_score,
                    "reasoning_score": reasoning_score,
                    "characteristics_score": characteristics_score
                },
                "explanation": self._generate_explanation(
                    content_score,
                    priority_score,
                    reasoning_score,
                    characteristics_score,
                    content
                )
            }
            
        except Exception as e:
            logger.error(f"Error in task priority analysis: {str(e)}")
            raise

    def _calculate_content_score(self, name: str, description: str) -> float:
        """Calculate score based on task name and description (40% weight)"""
        importance_keywords = {
            'urgent': 10,
            'critical': 10,
            'important': 8,
            'high priority': 8,
            'asap': 7,
            'deadline': 6,
            'crucial': 6,
            'essential': 5,
            'significant': 5,
            'key': 4
        }
        
        content = f"{name} {description}".lower()
        score = 0.0
        
        for keyword, weight in importance_keywords.items():
            if keyword in content:
                score += weight
        
        return min(score, 40.0)  # Cap at 40 as per weighting

    def _calculate_priority_score(self, priority: str) -> float:
        """Calculate score based on priority level (30% weight)"""
        priority_scores = {
            'urgent': 30.0,
            'high': 22.5,
            'normal': 15.0,
            'low': 7.5
        }
        return priority_scores.get(priority.lower(), 15.0)

    def _calculate_reasoning_score(self, reasoning: list) -> float:
        """Calculate score based on priority reasoning (20% weight)"""
        if not reasoning:
            return 10.0
        
        # Score based on number and quality of reasons
        base_score = min(len(reasoning) * 5, 20.0)
        return base_score

    def _calculate_characteristics_score(self, deadline: Optional[str], is_blocking: bool) -> float:
        """Calculate score based on task characteristics (10% weight)"""
        score = 0.0
        
        # Add points for having a deadline
        if deadline:
            score += 5.0
            
        # Add points for blocking status
        if is_blocking:
            score += 5.0
            
        return min(score, 10.0)

    def _generate_explanation(
        self,
        content_score: float,
        priority_score: float,
        reasoning_score: float,
        characteristics_score: float,
        content: Dict[str, Any]
    ) -> str:
        """Generate human-readable explanation for the score"""
        explanations = []
        
        if content_score > 30:
            explanations.append("Task content indicates high importance")
        elif content_score > 20:
            explanations.append("Task content suggests moderate importance")
            
        if priority_score > 22.5:
            explanations.append("High priority level")
        elif priority_score > 15:
            explanations.append("Moderate priority level")
            
        if reasoning_score > 15:
            explanations.append("Well-justified priority with multiple reasons")
        elif reasoning_score > 10:
            explanations.append("Adequately justified priority")
            
        if characteristics_score > 7.5:
            explanations.append("Critical task characteristics (blocking/deadline)")
            
        if not explanations:
            return "Score based on standard task analysis"
            
        return ". ".join(explanations) + "."

    def _calculate_time_risk_score(self, time_risk: Dict) -> float:
        """
        Calculate time risk score (0-1) based on various time-related factors.
        Returns a more aggressive score based on:
        - Deadline proximity vs remaining work (highest priority)
        - Progress rate and completion likelihood
        - Time buffer analysis
        - Work rate required vs historical rate
        """
        score = 0.0
        timeline = time_risk.get('timeline', {})
        
        # 1. Deadline Status and Time Buffer Analysis (50% weight)
        if time_risk.get('overdue', False):
            # Overdue tasks get nearly maximum score
            score += 0.45
            # Add remaining 0.05 based on how overdue
            days_overdue = abs(time_risk.get('days_to_deadline', 0))
            score += min(0.05, days_overdue * 0.01)
        elif 'days_to_deadline' in time_risk:
            days_to_deadline = time_risk['days_to_deadline']
            planned_hours = timeline.get('planned_hours', 0)
            remaining_hours = timeline.get('remaining_hours', 0)
            progress = timeline.get('progress_percentage', 0)
            
            # Calculate remaining work days needed
            remaining_work_days = remaining_hours / 8 if remaining_hours > 0 else (planned_hours * (100 - progress) / 100) / 8
            
            # Time buffer ratio (remaining time vs needed time)
            if days_to_deadline <= 0:
                buffer_score = 0.5  # Maximum score for this component
            else:
                buffer_ratio = days_to_deadline / (remaining_work_days if remaining_work_days > 0 else 0.1)
                if buffer_ratio <= 1:
                    # Critical: Less or equal time than needed
                    buffer_score = 0.5
                elif buffer_ratio <= 1.2:
                    # Very tight buffer (20% or less)
                    buffer_score = 0.45
                elif buffer_ratio <= 1.5:
                    # Tight buffer (50% or less)
                    buffer_score = 0.4
                elif buffer_ratio <= 2:
                    # Limited buffer (double time needed)
                    buffer_score = 0.35
                else:
                    # Comfortable buffer but still factor in absolute deadline
                    buffer_score = max(0.2, 0.35 - (buffer_ratio - 2) * 0.05)

            score += buffer_score

        # 2. Progress Rate Analysis (30% weight)
        elapsed_hours = timeline.get('elapsed_hours', 0)
        planned_hours = timeline.get('planned_hours', 0)
        progress = timeline.get('progress_percentage', 0)
        
        if planned_hours > 0 and elapsed_hours > 0:
            # Calculate actual progress rate (% per hour)
            actual_rate = progress / elapsed_hours if elapsed_hours > 0 else 0
            
            # Calculate required rate to complete on time
            remaining_progress = 100 - progress
            if time_risk.get('days_to_deadline'):
                remaining_hours = time_risk['days_to_deadline'] * 8  # Convert days to hours
                required_rate = remaining_progress / remaining_hours if remaining_hours > 0 else float('inf')
                
                # Compare actual vs required rate
                if actual_rate == 0:
                    score += 0.3  # No progress being made
                elif required_rate > actual_rate * 3:
                    score += 0.3  # Need to work 3x faster
                elif required_rate > actual_rate * 2:
                    score += 0.25  # Need to work 2x faster
                elif required_rate > actual_rate * 1.5:
                    score += 0.2  # Need to work somewhat faster
                else:
                    score += 0.1  # Current pace is sufficient

        # 3. Time Elapsed vs Planned Analysis (20% weight)
        if planned_hours > 0 and elapsed_hours > 0:
            time_ratio = elapsed_hours / planned_hours
            progress_ratio = progress / 100
            
            # Calculate efficiency ratio (progress % / time %)
            efficiency = progress_ratio / time_ratio if time_ratio > 0 else 0
            
            if efficiency < 0.3:  # Severely inefficient
                score += 0.2
            elif efficiency < 0.5:  # Very inefficient
                score += 0.15
            elif efficiency < 0.7:  # Inefficient
                score += 0.1
            elif efficiency < 0.9:  # Slightly inefficient
                score += 0.05
            # Efficient progress doesn't add to risk score

        # Final adjustments
        if time_risk.get('is_at_risk', False):
            # Add 10% to score if task is flagged as at risk
            score = min(1.0, score + 0.1)
            
        # Ensure minimum score based on deadline proximity
        if 'days_to_deadline' in time_risk:
            days_to_deadline = time_risk['days_to_deadline']
            if days_to_deadline <= 1:
                score = max(score, 0.9)  # At least 90% risk if 1 day or less
            elif days_to_deadline <= 2:
                score = max(score, 0.8)  # At least 80% risk if 2 days or less
            elif days_to_deadline <= 3:
                score = max(score, 0.7)  # At least 70% risk if 3 days or less

        return min(1.0, score)

    async def _analyze_time_risks(self, task: Task) -> Dict:
        """Analyze time-based risks using actual task data."""
        current_time = self._get_current_time()
        risk_factors = []
        is_at_risk = False
        estimated_delay_days = 0
        
        # Get task timeline data
        timeline = {
            'created_at': self._ensure_tz_aware(task.created_at),
            'started_at': self._ensure_tz_aware(task.start_date),
            'deadline': self._ensure_tz_aware(task.deadline),
            'planned_hours': task.planned_hours or 0,
            'elapsed_hours': 0,
            'remaining_hours': 0,
            'progress_percentage': task.progress or 0
        }
        
        # Calculate elapsed time
        if timeline['started_at']:
            elapsed_seconds = (current_time - timeline['started_at']).total_seconds()
            timeline['elapsed_hours'] = elapsed_seconds / 3600
            
            # Calculate remaining hours based on progress
            if timeline['planned_hours'] > 0:
                timeline['remaining_hours'] = (timeline['planned_hours'] * (100 - timeline['progress_percentage'])) / 100
                
                # Check if taking longer than planned
                if timeline['elapsed_hours'] > timeline['planned_hours'] * 1.2:
                    risk_factors.append(f"Task taking longer than planned ({int(timeline['elapsed_hours'])} vs {timeline['planned_hours']} hours)")
                    is_at_risk = True
                    # Calculate delay based on remaining work and progress rate
                    if timeline['progress_percentage'] > 0:
                        progress_rate = timeline['progress_percentage'] / timeline['elapsed_hours']  # % per hour
                        remaining_progress = 100 - timeline['progress_percentage']
                        estimated_remaining_hours = remaining_progress / progress_rate if progress_rate > 0 else timeline['remaining_hours']
                        estimated_delay_days = int((estimated_remaining_hours - timeline['remaining_hours']) / 8)
                    else:
                        estimated_delay_days = int((timeline['elapsed_hours'] - timeline['planned_hours']) / 8)

        # Check deadline status
        overdue = False
        days_to_deadline = None
        if timeline['deadline']:
            days_to_deadline = (timeline['deadline'] - current_time).days
            if days_to_deadline < 0:
                overdue = True
                risk_factors.append(f"Task is overdue by {abs(days_to_deadline)} days")
                is_at_risk = True
                estimated_delay_days = abs(days_to_deadline)
            elif days_to_deadline <= 2:
                risk_factors.append(f"Urgent: Only {days_to_deadline} days until deadline")
                is_at_risk = True
            elif days_to_deadline <= 5:
                risk_factors.append(f"Approaching deadline: {days_to_deadline} days remaining")
                is_at_risk = True

        # Check progress vs expected
        if timeline['started_at'] and timeline['deadline'] and timeline['progress_percentage'] < 100:
            total_duration = (timeline['deadline'] - timeline['started_at']).total_seconds()
            elapsed_duration = (current_time - timeline['started_at']).total_seconds()
            if total_duration > 0:
                expected_progress = min((elapsed_duration / total_duration) * 100, 100)
                if timeline['progress_percentage'] < expected_progress - 20:
                    risk_factors.append(f"Behind schedule: {timeline['progress_percentage']}% complete vs {int(expected_progress)}% expected")
                    is_at_risk = True

        # Calculate time risk percentage using the formula: Risk (%) = (T_alloc / (T_left + ε)) * 100
        time_risk_percentage = 0
        if timeline['deadline']:
            allocated_hours = timeline['planned_hours']
            time_left_hours = max(0, (timeline['deadline'] - current_time).total_seconds() / 3600)
            epsilon = 1  # Small number to avoid division by zero
            
            if time_left_hours + epsilon > 0:
                time_risk_percentage = (allocated_hours / (time_left_hours + epsilon)) * 100
            else:
                time_risk_percentage = 200  # Extreme risk when no time left

        # Determine risk level based on percentage
        risk_level = "low"
        if time_risk_percentage >= 200:
            risk_level = "extreme"
        elif time_risk_percentage >= 150:
            risk_level = "critical"
        elif time_risk_percentage >= 100:
            risk_level = "high"
        elif time_risk_percentage >= 60:
            risk_level = "medium"
        elif time_risk_percentage >= 30:
            risk_level = "low"
        else:
            risk_level = "minimal"

        # Add cache_info for proper cache management
        cache_info = {
            "next_update": (current_time + timedelta(hours=1)).isoformat(),
            "update_frequency": "1 hour",
            "last_calculated": current_time.isoformat()
        }

        return {
            "is_at_risk": is_at_risk,
            "risk_factors": risk_factors,
            "estimated_delay_days": estimated_delay_days,
            "time_risk_percentage": round(time_risk_percentage, 2),
            "risk_level": risk_level,
            "timeline": {
                "created_at": timeline['created_at'].isoformat(),
                "started_at": timeline['started_at'].isoformat() if timeline['started_at'] else None,
                "deadline": timeline['deadline'].isoformat() if timeline['deadline'] else None,
                "planned_hours": timeline['planned_hours'],
                "elapsed_hours": timeline.get('elapsed_hours', 0),
                "remaining_hours": timeline.get('remaining_hours', 0),
                "progress_percentage": timeline['progress_percentage']
            },
            "overdue": overdue,
            "days_to_deadline": days_to_deadline,
            "progress": timeline['progress_percentage'],
            "cache_info": cache_info
        }

    async def _analyze_comments_ai(
        self,
        task_comments: List[Dict],
        project_comments: List[Dict],
        task_name: str,
        task_deadline: Optional[datetime],
        current_time: datetime
    ) -> Dict:
        """
        Advanced AI analysis for comments to assess communication risk and sentiment.
        Analyzes comments for sentiment, urgency, promises, and risk indicators.
        Returns a comprehensive analysis with actionable insights.
        """
        try:
            # Combine and sort all comments by date (most recent first)
            all_comments = []
            
            for comment in task_comments:
                all_comments.append({
                    **comment,
                    'type': 'task',
                    'date': datetime.fromisoformat(comment['created_at'].replace('Z', '+00:00'))
                })
            
            for comment in project_comments:
                all_comments.append({
                    **comment,
                    'type': 'project',
                    'date': datetime.fromisoformat(comment['created_at'].replace('Z', '+00:00'))
                })
            
            # Sort by date (most recent first) and take last 10 for better context
            all_comments.sort(key=lambda x: x['date'], reverse=True)
            recent_comments = all_comments[:10]
            
            # Enhanced prompt for comprehensive comments analysis
            prompt = f"""You are an expert project manager and communication analyst. Analyze the following task and its communication patterns to assess risk and provide actionable insights.

CRITICAL RULE: Communication and sentiment are SEPARATE factors that combine to create the total risk score.

TASK CONTEXT:
Task Name: {task_name}
Task Deadline: {task_deadline.isoformat() if task_deadline else 'No deadline'}
Current Date: {current_time.isoformat()}
Days to Deadline: {(task_deadline - current_time).days if task_deadline else 'No deadline'}

COMMUNICATION ANALYSIS:
{self._format_comments_for_analysis(recent_comments, current_time)}

ANALYSIS REQUIREMENTS:

1. COMMUNICATION SCORE (0-10) - SEPARATE FROM SENTIMENT:
   - 0-2: Excellent communication, clear updates, realistic promises, active engagement
   - 3-4: Good communication, some clarity issues, generally positive
   - 5-6: Moderate communication, some concerns, mixed signals
   - 7-8: Poor communication, vague responses, concerning patterns, delays
   - 9-10: Very poor communication, red flags, broken promises, no engagement

2. SENTIMENT SCORE (0-10) - SEPARATE FROM COMMUNICATION:
   - 0-2: Very positive sentiment, confidence, enthusiasm, solutions
   - 3-4: Positive sentiment, generally optimistic, constructive
   - 5-6: Neutral sentiment, mixed emotions, balanced
   - 7-8: Negative sentiment, frustration, confusion, delays
   - 9-10: Very negative sentiment, anger, blame, hopelessness

3. COMBINED RISK SCORE (0-10):
   - Communication Score (50% weight) + Sentiment Score (50% weight)
   - Example: Communication 6 + Sentiment 4 = Combined Score 5.0

4. NO COMMENTS SCENARIO:
   If no comments exist:
   - Communication Score: 10 (maximum risk - no communication)
   - Sentiment Score: 5 (neutral - no sentiment to analyze)
   - Combined Score: 7.5

5. SENTIMENT ANALYSIS (CRITICAL FOR RISK ASSESSMENT):
   - Positive: Confidence, progress, solutions, collaboration, enthusiasm
   - Neutral: Informational, status updates, questions, balanced
   - Negative: Frustration, confusion, delays, problems, blame, anger
   - Urgent: Time pressure, deadlines, immediate action needed

6. RISK FACTORS TO IDENTIFY:
   - Promises made vs. timeline reality
   - Communication frequency and quality
   - Signs of stress, confusion, or delays
   - Commitment level and accountability
   - Technical vs. non-technical communication gaps
   - Team collaboration issues
   - Scope creep or requirement changes
   - Resource or dependency problems

You MUST return ONLY valid JSON in this exact format:
{{
    "communication_score": 5.0,
    "sentiment_score": 4.0,
    "combined_score": 4.5,
    "risk_level": "medium",
    "sentiment_overall": "neutral",
    "sentiment_breakdown": {{
        "positive": 0.3,
        "neutral": 0.5,
        "negative": 0.2,
        "urgent": 0.1
    }},
    "analysis_details": "Detailed analysis of communication patterns and risk factors",
    "promises_made": ["List of specific promises found in comments"],
    "promises_kept": ["List of promises that appear to be fulfilled"],
    "promises_broken": ["List of promises that appear to be broken"],
    "risk_indicators": ["List of specific risk indicators found"],
    "communication_quality": "Good/Poor/Excellent/Concerning",
    "timeline_commitments": ["List of timeline commitments mentioned"],
    "collaboration_issues": ["List of collaboration problems identified"],
    "technical_challenges": ["List of technical issues mentioned"],
    "scope_changes": ["List of scope or requirement changes"],
    "urgency_signals": ["List of urgent or time-sensitive mentions"],
    "positive_signals": ["List of positive progress indicators"],
    "recommendations": ["List of actionable recommendations"],
    "overall_assessment": "Summary of communication risk assessment",
    "engagement_level": "High/Medium/Low",
    "communication_frequency": "Frequent/Occasional/Rare/None",
    "no_comments_risk": "High/Medium/Low (only if no comments exist)"
}}

IMPORTANT: 
- Communication score and sentiment score are SEPARATE
- Combined score = (communication_score + sentiment_score) / 2
- If there are comments, communication score should be LOWER (better)
- Sentiment score reflects the emotional tone of the comments

Return only valid JSON, no other text."""

            logger.info(f"Starting advanced AI comments analysis for task {task_name} with {len(recent_comments)} comments")
            
            response = requests.post(
                self.ollama_url,
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": True
                },
                timeout=60,
                stream=True
            )
            
            if response.status_code != 200:
                logger.error(f"AI service returned status {response.status_code}: {response.text}")
                raise Exception(f"AI service error: {response.status_code}")
            
            # Collect streaming response
            ai_response_text = ""
            logger.info("Receiving AI comments analysis stream:")
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        if 'response' in chunk:
                            ai_response_text += chunk['response']
                            logger.info(f"AI comments chunk: {chunk['response']}")
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"Complete AI comments response: {ai_response_text}")
            
            # Try to parse JSON response
            try:
                analysis = json.loads(ai_response_text)
                logger.info(f"Parsed AI comments analysis: {json.dumps(analysis, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI comments JSON response: {e}")
                logger.error(f"Raw AI comments response: {ai_response_text}")
                # Fallback to enhanced manual analysis
                return self._enhanced_fallback_comments_analysis(recent_comments, current_time, task_name, task_deadline)
            
            # Validate required fields
            required_fields = ['communication_score', 'sentiment_score', 'combined_score', 'risk_level', 'sentiment_overall', 'sentiment_breakdown', 'analysis_details', 'promises_made', 'promises_kept', 'promises_broken', 'risk_indicators', 'communication_quality', 'timeline_commitments', 'collaboration_issues', 'technical_challenges', 'scope_changes', 'urgency_signals', 'positive_signals', 'recommendations', 'overall_assessment', 'engagement_level', 'communication_frequency', 'no_comments_risk']
            missing_fields = [field for field in required_fields if field not in analysis]
            
            if missing_fields:
                logger.warning(f"AI comments response missing fields: {missing_fields}")
                return self._enhanced_fallback_comments_analysis(recent_comments, current_time, task_name, task_deadline)
            
            return {
                "ai_analysis_performed": True,
                "communication_score": round(float(analysis.get('communication_score', 5)), 2),
                "sentiment_score": round(float(analysis.get('sentiment_score', 4)), 2),
                "combined_score": round(float(analysis.get('combined_score', 4.5)), 2),
                "risk_level": analysis.get('risk_level', 'medium'),
                "sentiment_overall": analysis.get('sentiment_overall', 'neutral'),
                "sentiment_breakdown": analysis.get('sentiment_breakdown', {}),
                "analysis_details": analysis.get('analysis_details', 'No analysis details provided'),
                "promises_made": analysis.get('promises_made', []),
                "promises_kept": analysis.get('promises_kept', []),
                "promises_broken": analysis.get('promises_broken', []),
                "risk_indicators": analysis.get('risk_indicators', []),
                "communication_quality": analysis.get('communication_quality', 'Unknown'),
                "timeline_commitments": analysis.get('timeline_commitments', []),
                "collaboration_issues": analysis.get('collaboration_issues', []),
                "technical_challenges": analysis.get('technical_challenges', []),
                "scope_changes": analysis.get('scope_changes', []),
                "urgency_signals": analysis.get('urgency_signals', []),
                "positive_signals": analysis.get('positive_signals', []),
                "recommendations": analysis.get('recommendations', []),
                "overall_assessment": analysis.get('overall_assessment', 'No assessment provided'),
                "engagement_level": analysis.get('engagement_level', 'Unknown'),
                "communication_frequency": analysis.get('communication_frequency', 'Unknown'),
                "no_comments_risk": analysis.get('no_comments_risk', None),
                "comments_analyzed": len(recent_comments),
                "recent_comments": recent_comments
            }
            
        except Exception as e:
            logger.error(f"Error in AI comments analysis: {str(e)}")
            return self._enhanced_fallback_comments_analysis(task_comments + project_comments, current_time, task_name, task_deadline)

    def _format_comments_for_analysis(self, comments: List[Dict], current_time: datetime) -> str:
        """Format comments for AI analysis with context"""
        if not comments:
            return "NO COMMENTS FOUND - This could indicate communication issues or lack of engagement."
        
        formatted_comments = []
        for comment in comments:
            days_ago = (current_time - comment['date']).days
            hours_ago = (current_time - comment['date']).total_seconds() / 3600
            
            if hours_ago < 24:
                time_str = f"{int(hours_ago)} hours ago"
            else:
                time_str = f"{days_ago} days ago"
            
            comment_type = comment.get('type', 'unknown')
            author = comment.get('author_name', 'Unknown')
            content = comment.get('content', '')
            
            formatted_comments.append(f"[{time_str}] {author} ({comment_type}): {content}")
        
        return "\n".join(formatted_comments)

    def _enhanced_fallback_comments_analysis(
        self,
        comments: List[Dict],
        current_time: datetime,
        task_name: str,
        task_deadline: Optional[datetime]
    ) -> Dict:
        """
        Enhanced fallback analysis when AI fails.
        Provides intelligent analysis even without AI, including no-comments scenarios.
        NO COMMENTS = MAXIMUM RISK (10/10) - Lack of communication is a major red flag.
        """
        try:
            if not comments:
                # NO COMMENTS = MAXIMUM RISK (10/10) - This is a major red flag
                communication_score = 10.0  # MAXIMUM RISK
                sentiment_score = 5.0  # NEUTRAL - NO SENTIMENT
                combined_score = 7.5  # COMBINED SCORE
                risk_level = "extreme"
                
                # Provide detailed analysis of why no comments is high risk
                if task_deadline and (task_deadline - current_time).days < 0:
                    analysis_details = "CRITICAL: Task is overdue with NO COMMUNICATION - EXTREME RISK (10/10). No comments indicates: 1) Task is completely stuck and assignee is not asking for help, 2) Task is being ignored or forgotten, 3) Complete communication breakdown, 4) Task requirements are unclear and no one is clarifying, 5) Team is not engaged at all."
                elif task_deadline and (task_deadline - current_time).days <= 3:
                    analysis_details = "HIGH RISK: Task due soon with NO COMMUNICATION - EXTREME RISK (10/10). No comments indicates: 1) Task is likely stuck and assignee is not communicating, 2) Task requirements are unclear and no questions are being asked, 3) Team is not engaged or aware of the task, 4) Potential for complete failure due to lack of communication."
                else:
                    analysis_details = "HIGH RISK: Task with NO COMMUNICATION - EXTREME RISK (10/10). No comments indicates: 1) Task is unclear and team is not asking questions, 2) Lack of team engagement and ownership, 3) Task may be progressing silently (unlikely) or completely stuck, 4) No accountability or progress tracking."
                
                return {
                    "ai_analysis_performed": False,
                    "communication_score": communication_score,  # MAXIMUM RISK
                    "sentiment_score": sentiment_score,  # NEUTRAL - NO SENTIMENT
                    "combined_score": combined_score,  # COMBINED SCORE
                    "risk_level": risk_level,
                    "sentiment_overall": "negative",  # No communication = negative sentiment
                    "sentiment_breakdown": {"positive": 0.0, "neutral": 0.0, "negative": 1.0, "urgent": 0.0},
                    "analysis_details": analysis_details,
                    "promises_made": [],
                    "promises_kept": [],
                    "promises_broken": [],
                    "risk_indicators": [
                        "NO COMMUNICATION - Major red flag",
                        "Lack of team engagement", 
                        "Unclear task status",
                        "No progress tracking",
                        "Potential for complete failure"
                    ],
                    "communication_quality": "Critical",  # No communication = critical quality
                    "timeline_commitments": [],
                    "collaboration_issues": [
                        "Complete lack of team communication",
                        "No collaboration happening",
                        "Task may be forgotten or ignored"
                    ],
                    "technical_challenges": [],
                    "scope_changes": [],
                    "urgency_signals": [],
                    "positive_signals": [],
                    "recommendations": [
                        "IMMEDIATE ACTION REQUIRED: Schedule emergency team meeting",
                        "Contact assignee immediately to check task status",
                        "Clarify task requirements and expectations",
                        "Establish daily communication check-ins",
                        "Consider reassigning task if current assignee is unresponsive"
                    ],
                    "overall_assessment": f"CRITICAL: No communication detected - EXTREME RISK (10/10). Task requires immediate attention and intervention.",
                    "engagement_level": "None",  # No engagement
                    "communication_frequency": "None",  # No communication
                    "no_comments_risk": "extreme",  # Maximum risk
                    "comments_analyzed": 0,
                    "recent_comments": []
                }
            
            # Enhanced rule-based analysis for existing comments
            communication_score = 5.0  # Default medium risk
            sentiment_score = 4.0  # NEUTRAL - NO SENTIMENT
            combined_score = 4.5  # COMBINED SCORE
            risk_indicators = []
            promises_made = []
            promises_kept = []
            promises_broken = []
            positive_signals = []
            urgency_signals = []
            technical_challenges = []
            collaboration_issues = []
            
            # Analyze comment content for various indicators
            for comment in comments:
                content = comment.get('content', '').lower()
                author = comment.get('author_name', 'Unknown')
                days_ago = (current_time - comment['date']).days
                
                # Check for risk indicators
                if any(word in content for word in ['delay', 'late', 'problem', 'issue', 'stuck', 'blocked', 'error', 'fail', 'broken']):
                    risk_indicators.append(f"Risk indicator in comment by {author}: {comment.get('content', '')[:50]}...")
                    communication_score += 1
                
                # Check for promises
                if any(word in content for word in ['will', 'promise', 'commit', 'finish', 'complete', 'done', 'deliver']):
                    promise_text = f"Promise by {author}: {comment.get('content', '')[:50]}..."
                    promises_made.append(promise_text)
                    
                    # Check if promise was kept (if it's an old comment)
                    if days_ago > 3:
                        if any(word in content for word in ['completed', 'finished', 'done', 'delivered']):
                            promises_kept.append(promise_text)
                        else:
                            promises_broken.append(promise_text)
                            communication_score += 1
                
                # Check for positive indicators
                if any(word in content for word in ['progress', 'done', 'completed', 'finished', 'success', 'working', 'good', 'great']):
                    positive_signals.append(f"Positive signal from {author}: {comment.get('content', '')[:50]}...")
                    sentiment_score -= 0.5
                
                # Check for urgency
                if any(word in content for word in ['urgent', 'asap', 'immediately', 'deadline', 'critical', 'emergency']):
                    urgency_signals.append(f"Urgency signal from {author}: {comment.get('content', '')[:50]}...")
                    communication_score += 0.5
                
                # Check for technical challenges
                if any(word in content for word in ['bug', 'error', 'technical', 'complex', 'difficult', 'challenge', 'issue']):
                    technical_challenges.append(f"Technical challenge mentioned by {author}: {comment.get('content', '')[:50]}...")
                    sentiment_score += 0.5
                
                # Check for collaboration issues
                if any(word in content for word in ['waiting', 'blocked', 'dependency', 'need help', 'confused', 'unclear']):
                    collaboration_issues.append(f"Collaboration issue from {author}: {comment.get('content', '')[:50]}...")
                    communication_score += 0.5
            
            # Cap score between 0 and 10
            communication_score = max(0, min(10, communication_score))
            sentiment_score = max(0, min(10, sentiment_score))
            
            # Calculate combined score
            combined_score = (communication_score + sentiment_score) / 2
            
            # Determine risk level
            if communication_score <= 3:
                risk_level = "low"
                communication_quality = "Good"
            elif communication_score <= 6:
                risk_level = "medium"
                communication_quality = "Moderate"
            else:
                risk_level = "high"
                communication_quality = "Poor"
            
            # Determine sentiment overall
            if sentiment_score <= 2:
                sentiment_overall = "positive"
            elif sentiment_score <= 4:
                sentiment_overall = "neutral"
            else:
                sentiment_overall = "negative"
            
            # Determine engagement level
            if len(comments) >= 5:
                engagement_level = "High"
                communication_frequency = "Frequent"
            elif len(comments) >= 2:
                engagement_level = "Medium"
                communication_frequency = "Occasional"
            else:
                engagement_level = "Low"
                communication_frequency = "Rare"
            
            # Generate recommendations
            recommendations = []
            if communication_score > 6:
                recommendations.append("Schedule a team meeting to address communication issues")
                recommendations.append("Establish regular status update frequency")
            if technical_challenges:
                recommendations.append("Provide technical support or resources")
            if collaboration_issues:
                recommendations.append("Improve team collaboration and dependency management")
            if not positive_signals:
                recommendations.append("Encourage positive progress reporting")
            
            return {
                "ai_analysis_performed": False,
                "communication_score": round(communication_score, 2),
                "sentiment_score": round(sentiment_score, 2),
                "combined_score": round(combined_score, 2),
                "risk_level": risk_level,
                "sentiment_overall": sentiment_overall,
                "sentiment_breakdown": {"positive": 0.3, "neutral": 0.5, "negative": 0.2, "urgent": 0.1},
                "analysis_details": f"Enhanced rule-based analysis of {len(comments)} comments",
                "promises_made": promises_made,
                "promises_kept": promises_kept,
                "promises_broken": promises_broken,
                "risk_indicators": risk_indicators,
                "communication_quality": communication_quality,
                "timeline_commitments": [],
                "collaboration_issues": collaboration_issues,
                "technical_challenges": technical_challenges,
                "scope_changes": [],
                "urgency_signals": urgency_signals,
                "positive_signals": positive_signals,
                "recommendations": recommendations,
                "overall_assessment": f"Communication risk score: {communication_score}/10, Sentiment score: {sentiment_score}/10, Combined: {combined_score}/10 - {risk_level.upper()} RISK",
                "engagement_level": engagement_level,
                "communication_frequency": communication_frequency,
                "no_comments_risk": None,
                "comments_analyzed": len(comments),
                "recent_comments": comments[:5]  # Last 5 comments
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced fallback comments analysis: {str(e)}")
            return {
                "ai_analysis_performed": False,
                "error": str(e),
                "communication_score": 10.0,  # Default to maximum risk on error
                "sentiment_score": 10.0,  # Default to maximum risk on error
                "combined_score": 10.0,  # Default to maximum risk on error
                "analysis_details": f"Enhanced fallback analysis failed: {str(e)}",
                "risk_level": "extreme",
                "no_comments_risk": "extreme"  # Maximum risk
            }

    def _fallback_comments_analysis(
        self,
        comments: List[Dict],
        current_time: datetime
    ) -> Dict:
        """
        Fallback analysis when AI fails or provides incomplete data.
        Now calls the enhanced fallback analysis for better results.
        """
        return self._enhanced_fallback_comments_analysis(comments, current_time, "Unknown Task", None)

    async def _analyze_task_dependencies_ai(
        self,
        current_task: Dict,
        project_tasks: List[Dict],
        project_context: Dict
    ) -> Dict:
        """
        AI-powered analysis to determine which tasks truly depend on the current task.
        Analyzes task relationships and calculates dependency risk score.
        """
        try:
            logger.info(f"Starting AI dependency analysis for task: {current_task['name']}")
            logger.info(f"Project context: {project_context['project_name']}")
            logger.info(f"Number of project tasks to analyze: {len(project_tasks)}")
            
            # Prepare project context for AI analysis
            project_tasks_formatted = []
            for task in project_tasks:
                project_tasks_formatted.append({
                    'id': task['id'],
                    'name': task['name'],
                    'description': task['description'],
                    'state': task['state'],
                    'progress': task['progress']
                })
            
            # Create comprehensive AI prompt for dependency analysis
            prompt = f"""You are an expert project manager analyzing task dependencies. Analyze which tasks in the project truly depend on the current task.

PROJECT CONTEXT:
Project Name: {project_context['project_name']}
Project Description: {project_context['project_description']}
Total Project Tasks: {project_context['total_project_tasks']}

CURRENT TASK (being analyzed):
Name: {current_task['name']}
Description: {current_task['description']}

AVAILABLE TASKS IN PROJECT:
{self._format_project_tasks_for_analysis(project_tasks_formatted)}

DEPENDENCY ANALYSIS REQUIREMENTS:

1. DEPENDENCY SCORE (0-10):
   - 0: No tasks depend on this task
   - 1-3: Few tasks depend on this task (low impact)
   - 4-6: Several tasks depend on this task (medium impact)
   - 7-9: Many tasks depend on this task (high impact)
   - 10: ALL tasks depend on this task (critical blocker)

2. DEPENDENCY TYPES TO CONSIDER:
   - Direct Dependencies: Tasks that cannot start without this task
   - Sequential Dependencies: Tasks that follow this task in workflow
   - Resource Dependencies: Tasks that need resources from this task
   - Data Dependencies: Tasks that need data/output from this task
   - Infrastructure Dependencies: Tasks that need setup/infrastructure from this task

3. ANALYSIS CRITERIA:
   - Logical workflow dependencies
   - Resource sharing dependencies
   - Data flow dependencies
   - Infrastructure dependencies
   - Timeline dependencies

4. RISK ASSESSMENT:
   - If this task is delayed, how many other tasks are affected?
   - What is the criticality of dependent tasks?
   - Are there alternative paths if this task fails?

You MUST return ONLY valid JSON in this exact format:
{{
    "dependency_score": 7.5,
    "risk_level": "high",
    "analysis_details": "Detailed explanation of dependency analysis",
    "dependent_tasks": [
        {{
            "task_name": "Task Name",
            "dependency_type": "direct/sequential/resource/data/infrastructure",
            "dependency_strength": "high/medium/low",
            "reasoning": "Why this task depends on the current task"
        }}
    ],
    "total_dependent_tasks": 3,
    "critical_dependencies": 2,
    "dependency_impact": "high/medium/low",
    "blocking_potential": "high/medium/low",
    "recommendations": [
        "List of recommendations based on dependency analysis"
    ],
    "overall_assessment": "Summary of dependency risk assessment"
}}

Return only valid JSON, no other text."""

            logger.info(f"AI dependency prompt created, length: {len(prompt)} characters")
            logger.info(f"Making AI request to: {self.ollama_url}")
            
            response = requests.post(
                self.ollama_url,
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": True
                },
                timeout=60,
                stream=True
            )
            
            logger.info(f"AI service response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"AI service returned status {response.status_code}: {response.text}")
                raise Exception(f"AI service error: {response.status_code}")
            
            # Collect streaming response
            ai_response_text = ""
            logger.info("Receiving AI dependency analysis stream:")
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line.decode('utf-8'))
                        if 'response' in chunk:
                            ai_response_text += chunk['response']
                            logger.info(f"AI dependency chunk: {chunk['response']}")
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"Complete AI dependency response: {ai_response_text}")
            
            # Try to parse JSON response
            try:
                analysis = json.loads(ai_response_text)
                logger.info(f"Parsed AI dependency analysis: {json.dumps(analysis, indent=2)}")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse AI dependency JSON response: {e}")
                logger.error(f"Raw AI dependency response: {ai_response_text}")
                # Fallback to enhanced manual analysis
                logger.info("Falling back to enhanced manual dependency analysis")
                return self._enhanced_fallback_dependency_analysis(current_task, project_tasks, project_context)
            
            # Validate required fields
            required_fields = ['dependency_score', 'risk_level', 'analysis_details']
            missing_fields = [field for field in required_fields if field not in analysis]
            
            if missing_fields:
                logger.warning(f"AI dependency response missing fields: {missing_fields}")
                logger.info("Falling back to enhanced manual dependency analysis due to missing fields")
                return self._enhanced_fallback_dependency_analysis(current_task, project_tasks, project_context)
            
            result = {
                "ai_analysis_performed": True,
                "dependency_score": round(float(analysis.get('dependency_score', 0)), 2),
                "risk_level": analysis.get('risk_level', 'low'),
                "analysis_details": analysis.get('analysis_details', 'No analysis details provided'),
                "dependent_tasks": analysis.get('dependent_tasks', []),
                "total_dependent_tasks": analysis.get('total_dependent_tasks', 0),
                "critical_dependencies": analysis.get('critical_dependencies', 0),
                "dependency_impact": analysis.get('dependency_impact', 'low'),
                "blocking_potential": analysis.get('blocking_potential', 'low'),
                "recommendations": analysis.get('recommendations', []),
                "overall_assessment": analysis.get('overall_assessment', 'No assessment provided'),
                "project_tasks_analyzed": len(project_tasks)
            }
            
            logger.info(f"Dependency analysis result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in AI dependency analysis: {str(e)}")
            logger.info("Falling back to enhanced manual dependency analysis due to error")
            return self._enhanced_fallback_dependency_analysis(current_task, project_tasks, project_context)

    def _format_project_tasks_for_analysis(self, project_tasks: List[Dict]) -> str:
        """Format project tasks for AI analysis"""
        if not project_tasks:
            return "No other tasks in project"
        
        formatted_tasks = []
        for task in project_tasks:
            formatted_tasks.append(f"- {task['name']}: {task['description']} (State: {task['state']}, Progress: {task['progress']}%)")
        
        return "\n".join(formatted_tasks)

    def _enhanced_fallback_dependency_analysis(
        self,
        current_task: Dict,
        project_tasks: List[Dict],
        project_context: Dict
    ) -> Dict:
        """
        Enhanced fallback dependency analysis when AI fails.
        Uses intelligent rule-based analysis to determine task dependencies.
        """
        try:
            if not project_tasks:
                return {
                    "ai_analysis_performed": False,
                    "dependency_score": 0.0,
                    "risk_level": "low",
                    "analysis_details": "No other tasks in project to analyze dependencies",
                    "dependent_tasks": [],
                    "total_dependent_tasks": 0,
                    "critical_dependencies": 0,
                    "dependency_impact": "low",
                    "blocking_potential": "low",
                    "recommendations": ["No dependencies to manage"],
                    "overall_assessment": "No dependency risk - single task project",
                    "project_tasks_analyzed": 0
                }
            
            # Rule-based dependency analysis
            current_task_name = current_task['name'].lower()
            current_task_desc = (current_task['description'] or '').lower()
            
            dependent_tasks = []
            dependency_score = 0.0
            critical_dependencies = 0
            
            logger.info(f"Analyzing dependencies for task: {current_task['name']}")
            logger.info(f"Current task keywords: {current_task_name}")
            
            # Analyze each project task for dependencies
            for task in project_tasks:
                task_name = task['name'].lower()
                task_desc = (task['description'] or '').lower()
                dependency_strength = "low"
                dependency_type = "sequential"
                reasoning = ""
                
                logger.info(f"Checking if task '{task['name']}' depends on '{current_task['name']}'")
                
                # Check for various types of dependencies
                
                # 1. Infrastructure/Hosting Dependencies
                if any(word in current_task_name for word in ['hosting', 'server', 'deploy', 'setup', 'infrastructure']):
                    if any(word in task_name for word in ['content', 'seo', 'develop', 'design', 'test']):
                        dependency_strength = "high"
                        dependency_type = "infrastructure"
                        reasoning = f"Task '{task['name']}' requires hosting infrastructure to be ready"
                        dependency_score += 2.5
                        critical_dependencies += 1
                        logger.info(f"Found infrastructure dependency: {task['name']} depends on {current_task['name']}")
                
                # 2. Design Dependencies (CRITICAL FOR DESIGN HOMEPAGE)
                elif any(word in current_task_name for word in ['design', 'wireframe', 'mockup', 'ui', 'ux']):
                    if any(word in task_name for word in ['develop', 'code', 'implement', 'build', 'html', 'css']):
                        dependency_strength = "high"
                        dependency_type = "sequential"
                        reasoning = f"Task '{task['name']}' cannot start without design being completed"
                        dependency_score += 2.5
                        critical_dependencies += 1
                        logger.info(f"Found design dependency: {task['name']} depends on {current_task['name']}")
                
                # 2.5. Specific check for "Design Homepage" -> "Develop Homepage" dependency
                elif current_task_name == "design homepage" and task_name == "develop homepage":
                    dependency_strength = "high"
                    dependency_type = "sequential"
                    reasoning = f"Task '{task['name']}' cannot start without design being completed - direct dependency"
                    dependency_score += 3.0  # Higher score for direct dependency
                    critical_dependencies += 1
                    logger.info(f"Found direct design->development dependency: {task['name']} depends on {current_task['name']}")
                
                # 3. Development Dependencies
                elif any(word in current_task_name for word in ['develop', 'code', 'build', 'implement']):
                    if any(word in task_name for word in ['test', 'deploy', 'hosting', 'content']):
                        dependency_strength = "medium"
                        dependency_type = "sequential"
                        reasoning = f"Task '{task['name']}' depends on development being completed"
                        dependency_score += 1.5
                        logger.info(f"Found development dependency: {task['name']} depends on {current_task['name']}")
                
                # 4. Content Dependencies
                elif any(word in current_task_name for word in ['content', 'write', 'text', 'copy']):
                    if any(word in task_name for word in ['seo', 'deploy', 'publish']):
                        dependency_strength = "medium"
                        dependency_type = "data"
                        reasoning = f"Task '{task['name']}' needs content to be ready"
                        dependency_score += 1.5
                        logger.info(f"Found content dependency: {task['name']} depends on {current_task['name']}")
                
                # 5. SEO Dependencies
                elif any(word in current_task_name for word in ['seo', 'optimization', 'metadata']):
                    if any(word in task_name for word in ['deploy', 'publish', 'launch']):
                        dependency_strength = "medium"
                        dependency_type = "data"
                        reasoning = f"Task '{task['name']}' depends on SEO optimization"
                        dependency_score += 1.5
                        logger.info(f"Found SEO dependency: {task['name']} depends on {current_task['name']}")
                
                # 6. Testing Dependencies
                elif any(word in current_task_name for word in ['test', 'testing', 'qa', 'quality']):
                    if any(word in task_name for word in ['deploy', 'publish', 'launch']):
                        dependency_strength = "high"
                        dependency_type = "sequential"
                        reasoning = f"Task '{task['name']}' cannot proceed without testing completion"
                        dependency_score += 2.0
                        critical_dependencies += 1
                        logger.info(f"Found testing dependency: {task['name']} depends on {current_task['name']}")
                
                # 7. Deployment Dependencies
                elif any(word in current_task_name for word in ['deploy', 'publish', 'launch', 'release']):
                    if any(word in task_name for word in ['monitor', 'maintain', 'support']):
                        dependency_strength = "medium"
                        dependency_type = "sequential"
                        reasoning = f"Task '{task['name']}' depends on deployment being completed"
                        dependency_score += 1.5
                        logger.info(f"Found deployment dependency: {task['name']} depends on {current_task['name']}")
                
                # If dependency found, add to list
                if dependency_strength != "low":
                    dependent_tasks.append({
                        "task_name": task['name'],
                        "dependency_type": dependency_type,
                        "dependency_strength": dependency_strength,
                        "reasoning": reasoning
                    })
                    logger.info(f"Added dependency: {task['name']} -> {current_task['name']} ({dependency_strength})")
            
            # Calculate final dependency score (cap at 10)
            dependency_score = min(dependency_score, 10.0)
            
            logger.info(f"Final dependency score: {dependency_score}/10")
            logger.info(f"Critical dependencies: {critical_dependencies}")
            logger.info(f"Total dependent tasks: {len(dependent_tasks)}")
            
            # Determine risk level
            if dependency_score >= 7:
                risk_level = "high"
                dependency_impact = "high"
                blocking_potential = "high"
            elif dependency_score >= 4:
                risk_level = "medium"
                dependency_impact = "medium"
                blocking_potential = "medium"
            else:
                risk_level = "low"
                dependency_impact = "low"
                blocking_potential = "low"
            
            # Generate recommendations
            recommendations = []
            if dependency_score > 5:
                recommendations.append("Prioritize this task as it blocks multiple other tasks")
                recommendations.append("Monitor dependent tasks for delays")
            if critical_dependencies > 0:
                recommendations.append("Focus on critical dependencies first")
            if len(dependent_tasks) > 3:
                recommendations.append("Consider breaking this task into smaller parts")
            
            if not recommendations:
                recommendations.append("No significant dependency risks identified")
            
            return {
                "ai_analysis_performed": False,
                "dependency_score": round(dependency_score, 2),
                "risk_level": risk_level,
                "analysis_details": f"Rule-based analysis of {len(project_tasks)} project tasks found {len(dependent_tasks)} dependencies",
                "dependent_tasks": dependent_tasks,
                "total_dependent_tasks": len(dependent_tasks),
                "critical_dependencies": critical_dependencies,
                "dependency_impact": dependency_impact,
                "blocking_potential": blocking_potential,
                "recommendations": recommendations,
                "overall_assessment": f"Dependency risk score: {dependency_score}/10 - {risk_level.upper()} RISK",
                "project_tasks_analyzed": len(project_tasks)
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced fallback dependency analysis: {str(e)}")
            return {
                "ai_analysis_performed": False,
                "error": str(e),
                "dependency_score": 0.0,
                "risk_level": "low",
                "analysis_details": f"Enhanced fallback analysis failed: {str(e)}",
                "dependent_tasks": [],
                "total_dependent_tasks": 0,
                "critical_dependencies": 0,
                "dependency_impact": "low",
                "blocking_potential": "low",
                "recommendations": ["Analysis failed - manual review recommended"],
                "overall_assessment": "Unable to assess dependencies",
                "project_tasks_analyzed": 0
        }

    def _serialize_datetime_objects(self, obj):
        """Recursively convert datetime objects to ISO format strings for JSON serialization"""
        if isinstance(obj, dict):
            return {key: self._serialize_datetime_objects(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime_objects(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    async def calculate_complete_task_risk(self, task_id: int) -> Dict:
        """
        Calculate complete weighted risk analysis for a task and store in database.
        
        This method:
        1. Collects all risk data using analyze_task_risk
        2. Calculates weighted component scores
        3. Computes final weighted risk score
        4. Stores results in TaskRisk table
        5. Returns complete analysis with stored data
        
        Component weights:
        - Time sensitivity: 30 points (30%)
        - Complexity: 20 points (20%)
        - Priority: 20 points (20%)
        - Role match: 20 points (20%)
        - Dependencies: 10 points (10%)
        - Comments: 10 points (10%)
        """
        try:
            # Get all risk data
            risk_data = await self.analyze_task_risk(task_id)
            
            if "error" in risk_data:
                raise ValueError(f"Error collecting risk data: {risk_data['error']}")
            
            collected_data = risk_data.get("collected_data", {})
            
            # Extract component scores
            time_risk_data = collected_data.get("time_risk_analysis", {})
            complexity_data = collected_data.get("task_complexity", {})
            assigned_person_data = collected_data.get("assigned_person", {})
            dependency_data = collected_data.get("task_dependencies", {})
            comments_data = collected_data.get("comments_analysis", {})
            task_details = collected_data.get("task_details", {})
            
            # Calculate component scores
            time_sensitivity_score = time_risk_data.get("weighted_risk_score", 15.0)
            
            # Handle complexity score conversion properly
            raw_complexity_score = complexity_data.get("complexity_score", 0)
            if isinstance(raw_complexity_score, (int, float)):
                complexity_score = (raw_complexity_score / 100) * 20  # Convert to 20-point scale
            else:
                complexity_score = 10.0  # Default medium complexity
            
            priority_score = self._calculate_priority_risk_score(task_details.get("priority", "medium"))
            role_match_score = assigned_person_data.get("total_score", 0)  # Already out of 20
            
            # Handle dependency score conversion properly
            raw_dependency_score = dependency_data.get("dependency_score", 0)
            if isinstance(raw_dependency_score, (int, float)):
                dependency_score = raw_dependency_score * 10  # Convert to 10-point scale
            else:
                dependency_score = 0.0  # Default no dependency risk
            
            comments_score = comments_data.get("communication_score", 5)  # Already out of 10
            
            # Calculate final weighted risk score (out of 100)
            final_risk_score = (
                time_sensitivity_score +
                complexity_score +
                priority_score +
                role_match_score +
                dependency_score +
                comments_score
            )
            
            # Determine risk level based on final score
            if final_risk_score >= 80:
                risk_level = "extreme"
            elif final_risk_score >= 60:
                risk_level = "critical"
            elif final_risk_score >= 40:
                risk_level = "high"
            elif final_risk_score >= 20:
                risk_level = "medium"
            elif final_risk_score >= 10:
                risk_level = "low"
            else:
                risk_level = "minimal"
            
            # Prepare risk factors and recommendations
            risk_factors = {
                "time_sensitivity": {
                    "score": time_sensitivity_score,
                    "details": time_risk_data.get("cached_time_risk", {}),
                    "risk_level": time_risk_data.get("risk_level", "medium")
                },
                "complexity": {
                    "score": complexity_score,
                    "details": complexity_data,
                    "risk_level": "high" if complexity_score > 10 else "medium" if complexity_score > 5 else "low"
                },
                "priority": {
                    "score": priority_score,
                    "details": {"priority": task_details.get("priority", "medium")},
                    "risk_level": "high" if priority_score > 10 else "medium" if priority_score > 5 else "low"
                },
                "role_match": {
                    "score": role_match_score,
                    "details": assigned_person_data.get("ai_analysis", {}),
                    "risk_level": "high" if role_match_score > 10 else "medium" if role_match_score > 5 else "low"
                },
                "dependencies": {
                    "score": dependency_score,
                    "details": dependency_data.get("ai_analysis", {}),
                    "risk_level": dependency_data.get("dependency_risk_level", "low")
                },
                "comments": {
                    "score": comments_score,
                    "details": comments_data,
                    "risk_level": "high" if comments_score > 5 else "medium" if comments_score > 2 else "low"
                }
            }
            
            # Generate recommendations
            recommendations = {
                "immediate_actions": [],
                "short_term": [],
                "long_term": []
            }
            
            # Time-based recommendations
            if time_sensitivity_score > 20:
                recommendations["immediate_actions"].append("Review task timeline and consider deadline extension")
            elif time_sensitivity_score > 15:
                recommendations["short_term"].append("Monitor task progress closely")
            
            # Complexity recommendations
            if complexity_score > 10:
                recommendations["immediate_actions"].append("Break down complex task into smaller subtasks")
            
            # Role match recommendations
            if role_match_score > 15:
                recommendations["immediate_actions"].append("Consider reassigning task to better-suited team member")
            elif role_match_score > 10:
                recommendations["short_term"].append("Provide additional training or support to assigned team member")
            
            # Dependency recommendations
            if dependency_score > 5:
                recommendations["short_term"].append("Review and resolve task dependencies")
            
            # Comments recommendations
            if comments_score > 5:
                recommendations["short_term"].append("Improve communication and collaboration on this task")
            
            # Store in database
            task_risk_crud = TaskRiskCRUD(self.db)
            
            # Serialize datetime objects for JSON storage
            serialized_risk_factors = self._serialize_datetime_objects(risk_factors)
            serialized_recommendations = self._serialize_datetime_objects(recommendations)
            serialized_metrics = self._serialize_datetime_objects(collected_data.get("metrics"))
            
            # Debug logging
            logger.info(f"Storing risk analysis for task {task_id}:")
            logger.info(f"  Risk score: {final_risk_score}")
            logger.info(f"  Risk level: {risk_level}")
            logger.info(f"  Component scores: time={time_sensitivity_score}, complexity={complexity_score}, priority={priority_score}, role={role_match_score}, deps={dependency_score}, comments={comments_score}")
            
            # Try to store in database, but don't fail if it doesn't work
            stored_risk = None
            database_record_id = None
            stored_in_database = False
            
            try:
                stored_risk = task_risk_crud.create_risk_analysis(
                    task_id=task_id,
                    risk_score=final_risk_score,
                    risk_level=risk_level,
                    time_sensitivity=time_sensitivity_score,
                    complexity=complexity_score,
                    priority=priority_score,
                    risk_factors=serialized_risk_factors,
                    recommendations=serialized_recommendations,
                    metrics=serialized_metrics
                )
                database_record_id = stored_risk.id
                stored_in_database = True
                logger.info(f"Successfully stored risk analysis in database with ID: {database_record_id}")
            except Exception as db_error:
                logger.warning(f"Failed to store risk analysis in database: {str(db_error)}")
                logger.warning("Continuing with analysis results without database storage")
                stored_in_database = False
            
            # Return complete analysis
            return {
                "task_id": task_id,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "risk_score": round(final_risk_score, 2),
                "risk_level": risk_level,
                
                # Component scores
                "time_sensitivity": round(time_sensitivity_score, 2),
                "complexity": round(complexity_score, 2),
                "priority": round(priority_score, 2),
                "role_match": round(role_match_score, 2),
                "dependencies": round(dependency_score, 2),
                "comments": round(comments_score, 2),
                
                # Detailed analysis
                "risk_factors": risk_factors,
                "recommendations": recommendations,
                "metrics": collected_data.get("metrics"),
                
                # Analysis metadata
                "analysis_version": "1.0",
                "calculation_method": "weighted_component_analysis",
                "stored_in_database": stored_in_database,
                "database_record_id": database_record_id,
                
                # Component breakdown
                "component_breakdown": {
                    "time_sensitivity": {
                        "score": round(time_sensitivity_score, 2),
                        "weight": "30%",
                        "max_score": 30
                    },
                    "complexity": {
                        "score": round(complexity_score, 2),
                        "weight": "20%",
                        "max_score": 20
                    },
                    "priority": {
                        "score": round(priority_score, 2),
                        "weight": "20%",
                        "max_score": 20
                    },
                    "role_match": {
                        "score": round(role_match_score, 2),
                        "weight": "20%",
                        "max_score": 20
                    },
                    "dependencies": {
                        "score": round(dependency_score, 2),
                        "weight": "10%",
                        "max_score": 10
                    },
                    "comments": {
                        "score": round(comments_score, 2),
                        "weight": "10%",
                        "max_score": 10
                    }
                },
                
                # Raw data for reference
                "raw_analysis_data": risk_data
            }
            
        except Exception as e:
            logger.error(f"Error in complete risk analysis for task {task_id}: {str(e)}")
            logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise ValueError(f"Error calculating complete risk analysis: {str(e)}")

    def _calculate_priority_risk_score(self, priority: str) -> float:
        """Calculate priority risk score (0-20) based on task priority"""
        priority_scores = {
            "critical": 20.0,
            "high": 15.0,
            "medium": 10.0,
            "low": 5.0,
            "minimal": 2.0
        }
        return priority_scores.get(priority.lower(), 10.0)

# Create a singleton instance
_ai_service = None

def get_ai_service(db: Session) -> AIService:
    """Get or create singleton AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService(db)
    return _ai_service 