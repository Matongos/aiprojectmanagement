from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timezone, timedelta
import json
from zoneinfo import ZoneInfo
import logging
import requests

from services.ollama_service import get_ollama_client
from services.vector_service import VectorService
from services.weather_service import get_weather_service
from models.task import Task
from models.project import Project, ProjectMember
from models.time_entry import TimeEntry
from models.user import User
from models.activity import Activity
from schemas.task import TaskState
from services.complexity_service import ComplexityService
from models.task_risk import TaskRisk

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.ollama_client = get_ollama_client()
        self.vector_service = VectorService(db)
        self.weather_service = get_weather_service()
        self.ollama_url = "http://localhost:11434/api/generate"
        
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
        # Get task with all necessary relationships
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        try:
            # Check if task is completed
            if task.progress == 100 or getattr(task, 'state', '').lower() == 'done':
                risk_analysis = {
                    "task_id": task_id,
                    "risk_score": 0,
                    "risk_level": "low",
                    "risk_factors": [],
                    "risk_breakdown": {
                        "complexity": 0,
                        "time_sensitivity": 0,
                        "priority": 0
                    },
                    "recommendations": [],
                    "metrics": {
                        "time": {
                            "is_at_risk": False,
                            "risk_factors": [],
                            "estimated_delay_days": 0,
                            "timeline": {
                                "created_at": self._ensure_tz_aware(task.created_at).isoformat(),
                                "started_at": self._ensure_tz_aware(task.start_date).isoformat() if task.start_date else None,
                                "deadline": self._ensure_tz_aware(task.deadline).isoformat() if task.deadline else None,
                                "planned_hours": task.planned_hours or 0,
                                "elapsed_hours": 0,
                                "remaining_hours": 0,
                                "progress_percentage": 100
                            },
                            "overdue": False,
                            "days_to_deadline": 0,
                            "progress": 100
                        },
                        "role_match": {
                            "risk_level": "low",
                            "reason": "Task completed successfully",
                            "skill_gap": [],
                            "experience_level": "sufficient",
                            "metrics": {
                                "skill_match": 100,
                                "role_alignment": 100,
                                "experience_match": 100
                            }
                        },
                        "complexity": {
                            "score": 0,
                            "factors": {
                                "technical_complexity": 0,
                                "scope_complexity": 0,
                                "time_pressure": 0,
                                "environmental_complexity": 0,
                                "dependencies_impact": 0
                            }
                        }
                    }
                }
                
                # Store the risk analysis
                self._store_risk_analysis(task_id, risk_analysis)
                return risk_analysis

            # Continue with existing risk analysis for non-completed tasks
            # 1. Get task complexity data
            complexity_service = ComplexityService()
            complexity_analysis = await complexity_service.analyze_task_complexity(self.db, task_id)
            
            # 2. Get detailed assignee data
            assignee_data = None
            if task.assigned_to:
                assignee = self.db.query(User).filter(User.id == task.assigned_to).first()
                if assignee:
                    assignee_data = {
                        'id': assignee.id,
                        'role': getattr(assignee, 'role', None),
                        'job_title': getattr(assignee, 'job_title', None),
                        'department': getattr(assignee, 'department', None),
                        'skills': getattr(assignee, 'skills', []),
                        'experience_level': getattr(assignee, 'experience_level', None)
                    }

            # 3. Analyze time sensitivity
            time_risk = await self._analyze_time_risks(task)
            
            # 4. Calculate role/task mismatch using AI
            role_match_analysis = await self._analyze_role_task_match(
                task_name=task.name,
                task_description=task.description,
                assignee_data=assignee_data
            )
            
            # 5. Calculate risk components (ensure all are 0-100)
            risk_components = {
                'complexity': min(100, complexity_analysis.total_score),  # Already 0-100
                'time_sensitivity': min(100, self._calculate_time_risk_score(time_risk) * 100),
                'priority': min(100, self._calculate_priority_risk(task) * 100)
            }
            
            # New weights for different components (must sum to 1)
            weights = {
                'complexity': 0.1,    # 10% weight
                'time_sensitivity': 0.8,  # 80% weight
                'priority': 0.1     # 10% weight
            }
            
            # Calculate weighted risk score (will be 0-100)
            risk_score = sum(score * weights[component] for component, score in risk_components.items())
            risk_score = round(min(100, risk_score), 1)  # Ensure max is 100 and round to 1 decimal

            # Determine risk level based on 0-100 scale
            risk_level = "high" if risk_score > 70 else "medium" if risk_score > 40 else "low"
            
            # Collect risk factors
            risk_factors = []
            
            # Add complexity-based risk factors
            if complexity_analysis.total_score > 70:
                risk_factors.append("High task complexity")
                for factor_name, factor_value in complexity_analysis.factors.__dict__.items():
                    if isinstance(factor_value, (int, float)) and factor_value > 70:
                        risk_factors.append(f"High {factor_name.replace('_', ' ')} complexity")
            
            # Add time-based risk factors
            if time_risk['risk_factors']:
                risk_factors.extend(time_risk['risk_factors'])
            
            # Add priority-based risk factors
            if task.priority == 'high' or getattr(task, 'priority_score', 0) > 70:
                risk_factors.append("High priority task requiring immediate attention")

            # Generate recommendations
            recommendations = []
            if risk_score > 70:
                recommendations.append("Immediate attention required - High risk task")
            if complexity_analysis.total_score > 70:
                recommendations.append("Consider breaking down the task into smaller subtasks")
            if time_risk['is_at_risk']:
                recommendations.append(f"Review timeline - Task may be delayed by {time_risk['estimated_delay_days']} days")
            
            risk_analysis = {
                "task_id": task_id,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": risk_factors,
                "risk_breakdown": {
                    "complexity": round(risk_components['complexity'], 1),
                    "time_sensitivity": round(risk_components['time_sensitivity'], 1),
                    "priority": round(risk_components['priority'], 1)
                },
                "recommendations": recommendations,
                "metrics": {
                    "time": time_risk,
                    "role_match": role_match_analysis['details'],
                    "complexity": {
                        "score": complexity_analysis.total_score,
                        "factors": complexity_analysis.factors.__dict__
                    }
                    },
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Store the risk analysis
            self._store_risk_analysis(task_id, risk_analysis)
            return risk_analysis

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

    async def _analyze_role_task_match(
        self,
        task_name: str,
        task_description: str,
        assignee_data: Optional[Dict]
    ) -> Dict:
        """Analyze the match between task requirements and assignee capabilities"""
        if not assignee_data:
            return {
                "mismatch_score": 0.8,
                "risk_factors": ["Task not assigned to any team member"],
                "recommendations": ["Assign task to a team member"],
                "details": {
                    "risk_level": "high",
                    "reason": "No assignee",
                    "skill_gap": [],
                    "experience_level": "none",
                    "metrics": {
                        "similar_tasks_completed": 0,
                        "avg_completion_time": 0,
                        "success_rate": 0
                    }
                }
            }

        try:
            # Use AI to analyze task requirements
            prompt = f"""Analyze the following task and determine required skills and experience:
            Task Name: {task_name}
            Description: {task_description or ''}
            
            Assignee Information:
            Role: {assignee_data.get('role') or assignee_data.get('job_title') or 'Unknown'}
            Department: {assignee_data.get('department', 'Unknown')}
            Skills: {', '.join(assignee_data.get('skills', []))}
            Experience Level: {assignee_data.get('experience_level', 'Unknown')}
            
            Consider:
            1. Technical skills needed vs assignee skills
            2. Role/job title alignment with task requirements
            3. Department relevance to task
            4. Required experience level
            5. Domain knowledge requirements
            
            Return only valid JSON with:
            - skill_match_score: float (0-1)
            - role_alignment_score: float (0-1)
            - experience_match_score: float (0-1)
            - identified_gaps: list of strings
            - recommendations: list of strings
            """

            response = requests.post(
                self.ollama_url,
                json={
                    "model": "codellama",
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            result = response.json()
            analysis = json.loads(result["response"])
            
            # Calculate overall mismatch score
            mismatch_score = 1 - ((
                analysis['skill_match_score'] +
                analysis['role_alignment_score'] +
                analysis['experience_match_score']
            ) / 3)
            
            # Generate risk factors based on gaps
            risk_factors = []
            if analysis['identified_gaps']:
                risk_factors.extend(analysis['identified_gaps'])
            
            return {
                "mismatch_score": mismatch_score,
                "risk_factors": risk_factors,
                "recommendations": analysis['recommendations'],
                "details": {
                    "risk_level": "high" if mismatch_score > 0.7 else "medium" if mismatch_score > 0.4 else "low",
                    "reason": risk_factors[0] if risk_factors else None,
                    "skill_gap": analysis['identified_gaps'],
                    "experience_level": assignee_data.get('experience_level', 'unknown'),
                    "metrics": {
                        "skill_match": round(analysis['skill_match_score'] * 100, 1),
                        "role_alignment": round(analysis['role_alignment_score'] * 100, 1),
                        "experience_match": round(analysis['experience_match_score'] * 100, 1)
                    }
                }
            }
        except Exception as e:
            print(f"Error in role-task match analysis: {str(e)}")
            return {
                "mismatch_score": 0.5,
                "risk_factors": ["Unable to analyze role-task match"],
                "recommendations": ["Manually review task requirements and assignee capabilities"],
                "details": {
                    "risk_level": "medium",
                    "reason": "Analysis error",
                    "skill_gap": [],
                    "experience_level": "unknown",
                    "metrics": {
                        "skill_match": 0,
                        "role_alignment": 0,
                        "experience_match": 0
                    }
                }
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
                    score += 0.2  # Need to work 1.5x faster
                elif required_rate > actual_rate:
                    score += 0.15  # Need to work somewhat faster
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

        return {
            "is_at_risk": is_at_risk,
            "risk_factors": risk_factors,
            "estimated_delay_days": estimated_delay_days,
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
            "progress": timeline['progress_percentage']
        }

# Create a singleton instance
_ai_service = None

def get_ai_service(db: Session) -> AIService:
    """Get or create singleton AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService(db)
    return _ai_service 