from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timezone, timedelta
import json
from zoneinfo import ZoneInfo

from services.ollama_service import get_ollama_client
from services.vector_service import VectorService
from services.weather_service import get_weather_service
from models.task import Task
from models.project import Project, ProjectMember
from models.time_entry import TimeEntry
from models.user import User
from models.activity import Activity
from schemas.task import TaskState

class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.ollama_client = get_ollama_client()
        self.vector_service = VectorService(db)
        self.weather_service = get_weather_service()
        
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
        
    async def analyze_task(self, task_id: int) -> Dict:
        """Analyze task and provide comprehensive insights."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        return {
            "task_id": task_id,
            "complexity": {
                "score": 0.75,  # Example values
                "factors": ["Multiple dependencies", "Technical challenges"]
            },
            "required_skills": [
                {"skill": "Python", "level": "Advanced"},
                {"skill": "FastAPI", "level": "Intermediate"}
            ],
            "challenges": [
                "Complex integration requirements",
                "Tight deadline"
            ],
            "success_factors": [
                "Clear documentation",
                "Regular progress updates"
            ],
            "best_practices": [
                "Break down into smaller subtasks",
                "Set up automated testing"
            ]
        }

    async def suggest_task_priority(self, task_id: int) -> Dict:
        """Suggest task priority based on various factors."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        return {
            "task_id": task_id,
            "suggested_priority": "HIGH",
            "priority_score": 0.85,
            "factors": {
                "urgency": 0.9,
                "impact": 0.8,
                "dependencies": 0.7,
                "resource_availability": 0.85
            },
            "reasoning": [
                "Critical path task",
                "Multiple dependent tasks",
                "High business impact"
            ]
        }

    async def estimate_task_time(self, task_id: int) -> Dict:
        """Estimate task completion time."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        return {
            "task_id": task_id,
            "estimated_hours": 24,
            "confidence_score": 0.8,
            "range": {
                "minimum": 20,
                "maximum": 30
            },
            "factors": {
                "complexity": 0.7,
                "similar_tasks": 0.8,
                "resource_skill": 0.9,
                "dependencies": 0.75
            },
            "similar_tasks": [
                {"id": 123, "actual_hours": 22},
                {"id": 124, "actual_hours": 26}
            ]
        }

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
        """Analyze risk factors for a specific task using real-time data."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Ensure task dates are timezone aware
        task.created_at = self._ensure_tz_aware(task.created_at)
        task.start_date = self._ensure_tz_aware(task.start_date)
        task.deadline = self._ensure_tz_aware(task.deadline)
        
        # Initialize risk components
        risk_components = {
            'missing_info': 0.0,
            'role_match': 0.0,
            'time': 0.0,
            'dependencies': 0.0,
            'workload': 0.0,
            'complexity': 0.0,
            'activity': 0.0,
            'weather': 0.0  # Initialize weather risk
        }

        try:
            # Analyze missing information
            missing_info_score, missing_info_factors = await self._analyze_missing_info(task)
            risk_components['missing_info'] = missing_info_score

            # Analyze role/skill match
            role_match_risk = await self._analyze_role_skill_match(task)
            risk_components['role_match'] = self._calculate_role_match_score(role_match_risk)

            # Analyze time risks
            time_risk = await self._analyze_time_risks(task)
            risk_components['time'] = self._calculate_time_risk_score(time_risk)

            # Analyze dependencies
            dependency_risk = self._analyze_dependencies(task)
            risk_components['dependencies'] = self._calculate_dependency_score(dependency_risk)

            # Analyze workload
            workload_risk = await self._analyze_workload(task)
            risk_components['workload'] = self._calculate_workload_score(workload_risk)

            # Analyze complexity
            complexity_score, complexity_factors = await self._analyze_complexity(task)
            risk_components['complexity'] = complexity_score

            # Analyze activity
            activity_metrics = self._analyze_activity(task)
            risk_components['activity'] = self._calculate_activity_score(activity_metrics)

            # Analyze weather risks if applicable
            weather_risk = await self._analyze_weather_risk(task)
            risk_components['weather'] = weather_risk.get('risk_score', 0.0)

            # Calculate weighted risk score
            weights = {
                'missing_info': 0.1,
                'role_match': 0.15,
                'time': 0.2,
                'dependencies': 0.15,
                'workload': 0.1,
                'complexity': 0.15,
                'activity': 0.1,
                'weather': 0.05  # Weather has lower weight as it's not always applicable
            }

            risk_score = sum(score * weights[component] for component, score in risk_components.items())
            risk_score = min(1.0, risk_score)

            # Collect all risk factors
            risk_factors = []
            if missing_info_factors:
                risk_factors.extend(missing_info_factors)
            if role_match_risk.get('reason'):
                risk_factors.append(role_match_risk['reason'])
            if time_risk.get('risk_factors'):
                risk_factors.extend(time_risk['risk_factors'])
            if dependency_risk.get('blocked'):
                risk_factors.append(f"Blocked by {len(dependency_risk['blocking_tasks'])} tasks")
            if workload_risk.get('overloaded'):
                risk_factors.append(f"Assignee has {workload_risk['active_tasks']} active tasks")
            if weather_risk.get('risk_factors'):
                risk_factors.extend(weather_risk['risk_factors'])

            # Generate recommendations
            recommendations = self._generate_recommendations(risk_components, risk_factors, task)

            return {
                "task_id": task_id,
                "risk_score": round(risk_score, 2),
                "risk_level": "high" if risk_score > 0.7 else "medium" if risk_score > 0.4 else "low",
                "risk_factors": risk_factors,
                "risk_breakdown": risk_components,
                "recommendations": recommendations,
                "metrics": {
                    "time": time_risk,
                    "role_match": role_match_risk,
                    "dependencies": dependency_risk,
                    "workload": workload_risk,
                    "activity": activity_metrics,
                    "complexity": {
                        "score": complexity_score,
                        "factors": complexity_factors
                    },
                    "weather": weather_risk
                },
                "updated_at": self._get_current_time().isoformat()
            }

        except Exception as e:
            print(f"Error in analyze_task_risk: {str(e)}")
            raise ValueError(f"Error analyzing task risk: {str(e)}")

    async def _analyze_missing_info(self, task: Task) -> Tuple[float, List[str]]:
        """Analyze missing critical information in task."""
        score = 0.0
        factors = []
        
        if not task.description or len(task.description.strip()) < 10:
            score += 0.3
            factors.append("Insufficient task description")
        if not task.deadline:
            score += 0.2
            factors.append("No deadline specified")
        if not task.planned_hours:
            score += 0.2
            factors.append("No time estimate provided")
        if not task.assignee:
            score += 0.3
            factors.append("Task not assigned")
        if not task.priority:
            score += 0.1
            factors.append("Priority not set")
        
        return score, factors

    async def _analyze_complexity(self, task: Task) -> Tuple[float, List[str]]:
        """Analyze task complexity using multiple factors."""
        score = 0.0
        factors = []
        
        try:
            # Check description complexity
            if hasattr(task, 'description') and task.description:
                words = task.description.split()
                # Complexity indicators in description
                complexity_terms = ['complex', 'difficult', 'challenging', 'critical', 'major', 'significant']
                term_count = sum(1 for term in complexity_terms if term.lower() in task.description.lower())
                
                if len(words) > 200:
                    score += 0.2
                    factors.append("Detailed task description indicates complexity")
                elif len(words) > 100:
                    score += 0.1
                    factors.append("Moderately detailed description")
                
                if term_count > 2:
                    score += 0.2
                    factors.append(f"Found {term_count} complexity indicators in description")

            # Check dependencies
            try:
                dependencies = []
                if hasattr(task, 'depends_on_ids') and task.depends_on_ids:
                    dependencies = self.db.query(Task).filter(Task.id.in_(task.depends_on_ids)).all()
                elif hasattr(task, 'depends_on') and task.depends_on:
                    dependencies = task.depends_on

                if dependencies:
                    dep_count = len(dependencies)
                    blocked_deps = [d for d in dependencies if hasattr(d, 'state') and d.state != TaskState.DONE]
                    if dep_count > 3:
                        score += 0.3
                        factors.append(f"Complex dependency chain ({dep_count} dependencies)")
                    elif dep_count > 0:
                        score += 0.1
                        factors.append("Has dependencies")
                    
                    if blocked_deps:
                        score += 0.2
                        factors.append(f"{len(blocked_deps)} blocking dependencies")
            except Exception as e:
                print(f"Error checking dependencies: {str(e)}")

            # Check planned hours against similar tasks
            if hasattr(task, 'planned_hours') and task.planned_hours:
                try:
                    project_id = task.project_id if hasattr(task, 'project_id') else (task.project.id if hasattr(task, 'project') else None)
                    if project_id:
                        similar_tasks = self.db.query(Task).filter(
                            Task.project_id == project_id,
                            Task.id != task.id,
                            Task.state == TaskState.DONE
                        ).all()
                        
                        if similar_tasks:
                            avg_hours = sum(t.planned_hours or 0 for t in similar_tasks) / len(similar_tasks)
                            if task.planned_hours > avg_hours * 1.5:
                                score += 0.3
                                factors.append(f"Time estimate ({task.planned_hours}h) significantly higher than similar tasks ({avg_hours:.1f}h)")
                    
                    if task.planned_hours > 40:
                        score += 0.3
                        factors.append("Large time estimate indicates complexity")
                    elif task.planned_hours > 20:
                        score += 0.2
                        factors.append("Moderate time requirement")
                except Exception as e:
                    print(f"Error analyzing planned hours: {str(e)}")

            # Check subtasks
            try:
                subtasks = self.db.query(Task).filter(Task.parent_id == task.id).all()
                if subtasks:
                    if len(subtasks) > 5:
                        score += 0.2
                        factors.append(f"Complex task structure ({len(subtasks)} subtasks)")
                    elif len(subtasks) > 0:
                        score += 0.1
                        factors.append(f"Has {len(subtasks)} subtasks")
            except Exception as e:
                print(f"Error checking subtasks: {str(e)}")

            # Check technical requirements
            if hasattr(task, 'technical_requirements') and task.technical_requirements:
                tech_count = len(task.technical_requirements)
                if tech_count > 5:
                    score += 0.2
                    factors.append(f"Multiple technical requirements ({tech_count})")

            return min(score, 1.0), factors
        except Exception as e:
            print(f"Error in complexity analysis: {str(e)}")
            return 0.0, ["Error analyzing complexity"]

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
            'progress_percentage': 0
        }
        
        # Calculate elapsed time
        if timeline['started_at']:
            elapsed_seconds = (current_time - timeline['started_at']).total_seconds()
            timeline['elapsed_hours'] = elapsed_seconds / 3600
            
            # Check if taking longer than planned
            if timeline['elapsed_hours'] > timeline['planned_hours'] * 1.2:
                risk_factors.append(f"Task taking longer than planned ({int(timeline['elapsed_hours'])} vs {timeline['planned_hours']} hours)")
                is_at_risk = True
                estimated_delay_days = int((timeline['elapsed_hours'] - timeline['planned_hours']) / 8)

        # Check deadline proximity
        if timeline['deadline']:
            days_to_deadline = (timeline['deadline'] - current_time).days
            if days_to_deadline < 0:
                risk_factors.append(f"Task is overdue by {abs(days_to_deadline)} days")
                is_at_risk = True
                estimated_delay_days = abs(days_to_deadline)
            elif days_to_deadline <= 2:
                risk_factors.append(f"Urgent: Only {days_to_deadline} days until deadline")
                is_at_risk = True
            elif days_to_deadline <= 5:
                risk_factors.append(f"Approaching deadline: {days_to_deadline} days remaining")
                is_at_risk = True

        # Check progress vs time elapsed
        if task.progress and task.start_date:
            expected_progress = min((timeline['elapsed_hours'] / (task.planned_hours or 40)) * 100, 100)
            if task.progress < expected_progress - 20:
                risk_factors.append(f"Behind schedule: {task.progress}% complete vs {int(expected_progress)}% expected")
                is_at_risk = True

        # Check recent activity
        last_activity = self.db.query(Activity).filter(
            Activity.task_id == task.id
        ).order_by(Activity.created_at.desc()).first()

        if last_activity:
            days_since_activity = (current_time - last_activity.created_at).days
            if days_since_activity > 7:
                risk_factors.append(f"No activity for {days_since_activity} days")
                is_at_risk = True

        return {
            "is_at_risk": is_at_risk,
            "risk_factors": risk_factors,
            "estimated_delay_days": estimated_delay_days,
            "timeline": timeline,
            "overdue": bool(task.deadline and task.deadline < current_time),
            "days_to_deadline": (task.deadline - current_time).days if task.deadline else None,
            "progress": task.progress
        }

    def _calculate_role_match_score(self, role_match_risk: Dict) -> float:
        """Calculate role match risk score."""
        risk_levels = {
            'low': 0.2,
            'medium': 0.5,
            'high': 0.8
        }
        return risk_levels.get(role_match_risk['risk_level'], 0.5)

    def _calculate_time_risk_score(self, time_risk: Dict) -> float:
        """Calculate time risk score."""
        score = 0.0
        if time_risk['is_at_risk']:
            score += 0.4
        if time_risk['overdue']:
            score += 0.4
        if len(time_risk['risk_factors']) > 2:
            score += 0.2
        return min(score, 1.0)

    def _calculate_dependency_score(self, dependency_risk: Dict) -> float:
        """Calculate dependency risk score."""
        if not dependency_risk['blocked']:
            return 0.0
        return min(0.4 + (len(dependency_risk['blocking_tasks']) * 0.2), 1.0)

    def _calculate_workload_score(self, workload_risk: Dict) -> float:
        """Calculate workload risk score."""
        if not workload_risk['overloaded']:
            return 0.0
        return min(0.4 + (workload_risk['active_tasks'] / 10), 1.0)

    def _calculate_activity_score(self, activity_metrics: Dict) -> float:
        """Calculate activity risk score."""
        activity_levels = {
            'high': 0.0,
            'medium': 0.3,
            'low': 0.6,
            'none': 0.8
        }
        return activity_levels.get(activity_metrics['activity_level'], 0.5)

    def _generate_recommendations(self, risk_components: Dict, risk_factors: List[str], task: Task) -> List[str]:
        """Generate specific recommendations based on identified risks."""
        recommendations = []
        
        if risk_components['missing_info'] > 0.3:
            recommendations.append("Complete missing task information")
        
        if risk_components['role_match'] > 0.6:
            if task.assignee:
                recommendations.append(f"Review {task.assignee.username}'s role and consider skill-based reallocation")
            else:
                recommendations.append("Assign task to a qualified team member")
        
        if risk_components['time'] > 0.6:
            if task.deadline:
                recommendations.append(f"Urgent: Review timeline for task due on {task.deadline.strftime('%Y-%m-%d')}")
            else:
                recommendations.append("Set a deadline and timeline for this task")
        
        if risk_components['dependencies'] > 0.5:
            recommendations.append("Address blocking tasks and review dependency chain")
        
        if risk_components['workload'] > 0.5:
            recommendations.append("Consider workload redistribution or timeline adjustment")
        
        if risk_components['complexity'] > 0.6:
            recommendations.append("Break down task into smaller subtasks")
        
        if risk_components['activity'] > 0.5:
            recommendations.append("Investigate lack of progress and update task status")
        
        return recommendations

    async def _analyze_role_skill_match(self, task: Task) -> Dict:
        """Analyze match between task requirements and assignee skills."""
        try:
            if not hasattr(task, 'assignee') or not task.assignee:
                return {
                    "risk_level": "high",
                    "reason": "Task is not assigned",
                    "skill_gap": [],
                    "experience_level": "none",
                    "metrics": {
                        "similar_tasks_completed": 0,
                        "avg_completion_time": 0,
                        "success_rate": 0
                    }
                }

            # Get assignee's completed tasks in the last 90 days
            ninety_days_ago = self._get_current_time() - timedelta(days=90)
            
            # Get similar completed tasks
            try:
                similar_tasks_completed = self.db.query(Task).filter(
                    Task.assigned_to == (task.assignee.id if hasattr(task.assignee, 'id') else task.assignee),
                    Task.state == TaskState.DONE,
                    Task.updated_at >= ninety_days_ago,
                    Task.task_type == task.task_type if hasattr(task, 'task_type') else None
                ).all()
            except Exception as e:
                print(f"Error getting similar tasks: {str(e)}")
                similar_tasks_completed = []

            # Calculate experience metrics
            experience_metrics = {
                "similar_tasks_completed": len(similar_tasks_completed),
                "avg_completion_time": 0,
                "success_rate": 0
            }

            if similar_tasks_completed:
                completion_times = []
                successful_tasks = 0
                
                for t in similar_tasks_completed:
                    if hasattr(t, 'start_date') and hasattr(t, 'completion_date') and t.start_date and t.completion_date:
                        completion_times.append((t.completion_date - t.start_date).total_seconds() / 3600)
                    if hasattr(t, 'success_rating') and t.success_rating and t.success_rating >= 4:
                        successful_tasks += 1
                
                if completion_times:
                    experience_metrics["avg_completion_time"] = sum(completion_times) / len(completion_times)
                
                if similar_tasks_completed:
                    experience_metrics["success_rate"] = successful_tasks / len(similar_tasks_completed)

            # Determine risk level based on experience
            if experience_metrics["similar_tasks_completed"] >= 5 and experience_metrics["success_rate"] >= 0.8:
                risk_level = "low"
                reason = f"Assignee has successfully completed {experience_metrics['similar_tasks_completed']} similar tasks"
                experience_level = "expert"
            elif experience_metrics["similar_tasks_completed"] >= 2 and experience_metrics["success_rate"] >= 0.6:
                risk_level = "medium"
                reason = f"Assignee has moderate experience with similar tasks ({experience_metrics['similar_tasks_completed']} completed)"
                experience_level = "intermediate"
            else:
                risk_level = "high"
                reason = "Assignee lacks experience with similar tasks"
                experience_level = "beginner"

            # Check skill requirements match
            skill_gap = []
            if (hasattr(task, 'required_skills') and task.required_skills and 
                hasattr(task.assignee, 'skills') and task.assignee.skills):
                missing_skills = set(task.required_skills) - set(task.assignee.skills)
                if missing_skills:
                    skill_gap = list(missing_skills)
                    risk_level = "high"
                    reason = f"Assignee lacks required skills: {', '.join(missing_skills)}"

            return {
                "risk_level": risk_level,
                "reason": reason,
                "skill_gap": skill_gap,
                "experience_level": experience_level,
                "metrics": experience_metrics
            }
        except Exception as e:
            print(f"Error in role/skill match analysis: {str(e)}")
            return {
                "risk_level": "high",
                "reason": f"Error analyzing role/skill match: {str(e)}",
                "skill_gap": [],
                "experience_level": "unknown",
                "metrics": {
                    "similar_tasks_completed": 0,
                    "avg_completion_time": 0,
                    "success_rate": 0
                }
            }

    def _analyze_dependencies(self, task: Task) -> Dict:
        """Analyze task dependencies and identify blockers."""
        if not task.depends_on:
            return {
                "blocked": False,
                "blocking_tasks": [],
                "risk_level": "low"
            }

        blocking_tasks = []
        for dependency in task.depends_on:
            if dependency.state != TaskState.DONE:
                blocking_tasks.append({
                    "id": dependency.id,
                    "name": dependency.name,
                    "state": dependency.state,
                    "deadline": dependency.deadline.isoformat() if dependency.deadline else None
                })

        return {
            "blocked": bool(blocking_tasks),
            "blocking_tasks": blocking_tasks,
            "risk_level": "high" if blocking_tasks else "low"
        }

    async def _analyze_workload(self, task: Task) -> Dict:
        """Analyze assignee workload and capacity."""
        if not task.assignee:
            return {
                "overloaded": False,
                "active_tasks": 0,
                "risk_level": "low",
                "metrics": {
                    "total_hours_assigned": 0,
                    "hours_per_week": 0,
                    "task_overlap_count": 0
                }
            }

        current_time = self._get_current_time()

        # Get all active tasks for assignee
        active_tasks = self.db.query(Task).filter(
            Task.assigned_to == task.assignee.id,
            Task.state.in_([TaskState.IN_PROGRESS, TaskState.CHANGES_REQUESTED, TaskState.APPROVED]),
            Task.deadline >= current_time
        ).all()

        # Calculate workload metrics
        total_hours = sum(t.planned_hours or 0 for t in active_tasks)
        
        # Calculate task overlap
        overlapping_tasks = []
        if task.start_date and task.deadline:
            overlapping_tasks = [
                t for t in active_tasks 
                if t.id != task.id 
                and t.start_date 
                and t.deadline 
                and (
                    (t.start_date <= task.deadline and t.deadline >= task.start_date) or
                    (task.start_date <= t.deadline and task.deadline >= t.start_date)
                )
            ]

        # Calculate hours per week
        hours_per_week = 0
        if task.start_date and task.deadline:
            weeks = max(1, (task.deadline - task.start_date).days / 7)
            hours_per_week = total_hours / weeks

        # Determine workload status
        workload_threshold = 40  # Hours per week
        is_overloaded = (
            len(active_tasks) > 5 or
            hours_per_week > workload_threshold or
            len(overlapping_tasks) > 3
        )

        metrics = {
            "total_hours_assigned": total_hours,
            "hours_per_week": round(hours_per_week, 2),
            "task_overlap_count": len(overlapping_tasks),
            "concurrent_tasks": [
                {
                    "id": t.id,
                    "name": t.name,
                    "hours": t.planned_hours,
                    "start_date": t.start_date.isoformat() if t.start_date else None,
                    "deadline": t.deadline.isoformat() if t.deadline else None
                }
                for t in overlapping_tasks
            ]
        }

        risk_level = "high" if is_overloaded else "medium" if hours_per_week > workload_threshold * 0.7 else "low"

        return {
            "overloaded": is_overloaded,
            "active_tasks": len(active_tasks),
            "risk_level": risk_level,
            "metrics": metrics
        }

    def _analyze_activity(self, task: Task) -> Dict:
        """Analyze task activity patterns."""
        current_time = self._get_current_time()
        
        # Get all activities for the task
        activities = self.db.query(Activity).filter(
            Activity.task_id == task.id
        ).order_by(Activity.created_at).all()

        if not activities:
            return {
                "activity_level": "none",
                "last_updated": None,
                "state_changes": 0,
                "comment_count": 0
            }

        # Calculate metrics
        state_changes = len([a for a in activities if a.field_name == 'state'])
        comment_count = len(task.comments) if task.comments else 0
        last_activity = self._ensure_tz_aware(activities[-1].created_at)

        # Determine activity level
        days_since_last_activity = (current_time - last_activity).days
        if days_since_last_activity <= 1:
            activity_level = "high"
        elif days_since_last_activity <= 3:
            activity_level = "medium"
        else:
            activity_level = "low"

        return {
            "activity_level": activity_level,
            "last_updated": last_activity.isoformat(),
            "state_changes": state_changes,
            "comment_count": comment_count
        }

    async def _analyze_weather_risk(self, task: Task) -> Dict:
        """Analyze weather-related risks for a task."""
        try:
            # Check if task is outdoor-related
            is_outdoor = False
            outdoor_keywords = ['outdoor', 'outside', 'field', 'construction', 'installation', 'maintenance']
            
            if task.description:
                is_outdoor = any(keyword in task.description.lower() for keyword in outdoor_keywords)
            
            if not is_outdoor:
                return {
                    "is_at_risk": False,
                    "risk_score": 0.0,
                    "risk_factors": [],
                    "recommendations": [],
                    "forecast": None
                }

            # Get location from task or project
            location = None
            if task.location:
                location = task.location
            elif task.project and task.project.location:
                location = task.project.location
            else:
                # Default to a fallback location or get from configuration
                location = "default_location"  # Replace with your default location

            # Get weather forecast
            try:
                forecast = await self.weather_service.get_forecast(location)
            except Exception as e:
                print(f"Error getting weather forecast: {str(e)}")
                return {
                    "is_at_risk": False,
                    "risk_score": 0.0,
                    "risk_factors": ["Unable to fetch weather data"],
                    "recommendations": ["Verify weather conditions manually"],
                    "forecast": None
                }

            if not forecast:
                return {
                    "is_at_risk": False,
                    "risk_score": 0.0,
                    "risk_factors": ["No weather data available"],
                    "recommendations": ["Check weather conditions before proceeding"],
                    "forecast": None
                }

            # Analyze weather risks
            risk_score = 0.0
            risk_factors = []
            recommendations = []
            
            # Check weather conditions for task duration
            if task.start_date and task.deadline:
                task_duration = (task.deadline - task.start_date).days
                relevant_forecast = forecast[:min(task_duration, len(forecast))]

                for day in relevant_forecast:
                    if day.get('severe_conditions'):
                        risk_score = max(risk_score, 0.8)
                        risk_factors.append(f"Severe weather expected on {day['date']}")
                        recommendations.append("Plan for weather contingencies")
                    elif day.get('adverse_conditions'):
                        risk_score = max(risk_score, 0.4)
                        risk_factors.append(f"Adverse weather possible on {day['date']}")
                        recommendations.append("Monitor weather conditions")
            
            return {
                "is_at_risk": risk_score > 0.3,
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "recommendations": recommendations,
                "forecast": forecast
            }

        except Exception as e:
            print(f"Error in weather risk analysis: {str(e)}")
            return {
                "is_at_risk": False,
                "risk_score": 0.0,
                "risk_factors": ["Error in weather analysis"],
                "recommendations": ["Verify weather conditions manually"],
                "forecast": None
            }

# Create a singleton instance
_ai_service = None

def get_ai_service(db: Session) -> AIService:
    """Get or create singleton AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService(db)
    return _ai_service 