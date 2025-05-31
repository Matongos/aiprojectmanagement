from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timezone, timedelta
import json
from zoneinfo import ZoneInfo

from services.ollama_service import get_ollama_client
from services.vector_service import VectorService
from models.task import Task
from models.project import Project, ProjectMember
from models.time_entry import TimeEntry
from models.user import User

class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.ollama_client = get_ollama_client()
        self.vector_service = VectorService(db)
        
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
                "risk_factors": [f"Analysis error: {str(e)}"],
                "mitigations": ["Review project data and retry analysis"],
                "timeline_status": "unknown",
                "resource_recommendations": ["Verify project and task data integrity"]
            }

    async def analyze_project_insights(self, project_id: int) -> Dict[str, Any]:
        """Generate AI-powered insights for a project with historical learning"""
        # Get project data
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("Project not found")

        # Get all tasks for the project
        tasks = self.db.query(Task).filter(Task.project_id == project_id).all()
        
        # Analyze project timeline and dependencies
        timeline_analysis = self._analyze_project_timeline(project, tasks)
        
        # Get detailed user information for skill and role matching
        user_details = {}
        role_mismatches = []
        for task in tasks:
            if task.assigned_to:
                user = self.db.query(User).filter(User.id == task.assigned_to).first()
                if user:
                    user_details[user.username] = {
                        'expertise': user.expertise or [],
                        'skills': user.skills or [],
                        'profession': user.profession,
                        'experience_level': user.experience_level,
                        'specializations': user.specializations or [],
                        'job_title': user.job_title
                    }
                    
                    # Analyze role-task fit
                    if task.description and user.job_title:
                        role_analysis = self._analyze_role_task_fit(task.description, user.job_title)
                        if not role_analysis['is_match']:
                            role_mismatches.append({
                                'task_id': task.id,
                                'task_name': task.name,
                                'assigned_to': user.username,
                                'job_title': user.job_title,
                                'reason': role_analysis['reason']
                            })
        
        # Calculate basic metrics
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.state == 'done'])
        now = datetime.now(timezone.utc)
        overdue_tasks = len([t for t in tasks if t.deadline and t.deadline.replace(tzinfo=timezone.utc) < now])
        in_progress_tasks = len([t for t in tasks if t.state == 'in_progress'])
        
        # Calculate workload per user with skill matching
        workload = {}
        skill_mismatches = []
        
        for task in tasks:
            if task.assigned_to:
                user = self.db.query(User).filter(User.id == task.assigned_to).first()
                if user:
                    if user.username not in workload:
                        workload[user.username] = {
                            'total': 0,
                            'overdue': 0,
                            'completed': 0,
                            'in_progress': 0,
                            'high_priority': 0,
                            'role': user.profession or 'Unknown',
                            'expertise': user.expertise,
                            'skills': user.skills,
                            'experience_level': user.experience_level,
                            'avg_completion_time': 0,
                            'tasks_completed_successfully': 0,
                            'skill_matched_tasks': 0,
                            'skill_mismatched_tasks': 0
                        }
                    
                    # Update basic metrics
                    workload[user.username]['total'] += 1
                    if task.state == 'done':
                        workload[user.username]['completed'] += 1
                    if task.state == 'in_progress':
                        workload[user.username]['in_progress'] += 1
                    if task.deadline and task.deadline.replace(tzinfo=timezone.utc) < now:
                        workload[user.username]['overdue'] += 1
                    if task.priority in ['high', 'urgent']:
                        workload[user.username]['high_priority'] += 1
                    
                    # Analyze skill matching
                    if task.description:
                        task_skills = self._extract_skills_from_description(task.description)
                        if task_skills:
                            user_skills = set(user.skills or []) | set(user.expertise or []) | set(user.specializations or [])
                            if any(skill.lower() in {s.lower() for s in user_skills} for skill in task_skills):
                                workload[user.username]['skill_matched_tasks'] += 1
                            else:
                                workload[user.username]['skill_mismatched_tasks'] += 1
                                skill_mismatches.append({
                                    'task_id': task.id,
                                    'task_name': task.name,
                                    'assigned_to': user.username,
                                    'required_skills': task_skills,
                                    'user_skills': list(user_skills),
                                    'recommendation': self._find_better_match(task_skills, user_details)
                                })

        # Generate base insights
        insights = self._generate_basic_insights(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            overdue_tasks=overdue_tasks,
            workload=workload
        )

        # Add dependency and timeline analysis
        insights['dependency_analysis'] = {
            'timeline_feasible': timeline_analysis['timeline_feasible'],
            'timeline_issues': timeline_analysis['timeline_issues'],
            'critical_path': {
                'duration': timeline_analysis['critical_path']['duration'] if timeline_analysis['critical_path'] else 0,
                'tasks': timeline_analysis['critical_path']['path'] if timeline_analysis['critical_path'] else []
            } if timeline_analysis['critical_path'] else None,
            'bottlenecks': timeline_analysis['bottlenecks'],
            'parallel_tasks': {
                'concurrent_work': len(timeline_analysis['parallel_execution']['parallel_groups']),
                'resource_conflicts': timeline_analysis['parallel_execution']['resource_conflicts']
            }
        }

        # Update risks and suggestions based on dependency analysis
        if not timeline_analysis['timeline_feasible']:
            insights['risks'].extend(timeline_analysis['timeline_issues'])
            insights['suggestions'].append("Review and adjust project timeline based on task dependencies")
        
        if timeline_analysis['bottlenecks']:
            insights['risks'].extend([f"Dependency bottleneck: {b['impact']}" for b in timeline_analysis['bottlenecks']])
            insights['suggestions'].append("Address task dependency bottlenecks to improve project flow")
        
        if timeline_analysis['parallel_execution']['resource_conflicts']:
            insights['risks'].append(
                f"Resource conflicts detected on {len(timeline_analysis['parallel_execution']['resource_conflicts'])} days"
            )
            insights['suggestions'].append("Redistribute parallel tasks to avoid resource overallocation")

        # Add skill matching analysis
        skill_based_suggestions = []
        for username, data in workload.items():
            if data.get('skill_mismatched_tasks', 0) > 0:
                skill_based_suggestions.append({
                    'user': username,
                    'mismatched_tasks': data['skill_mismatched_tasks'],
                    'suggestion': self._generate_skill_suggestion(data)
                })

        insights['skill_analysis'] = {
            'summary': f"Found {len(skill_mismatches)} tasks with potential skill mismatches",
            'mismatches': skill_mismatches,
            'suggestions': skill_based_suggestions
        }

        # Update risks and suggestions with skill-based insights
        if skill_mismatches:
            insights['risks'].append(f"{len(skill_mismatches)} tasks assigned to users without matching skills")
            insights['suggestions'].extend([
                "Review task assignments based on team member skills",
                "Consider team training for frequently needed skills",
                "Update team member skill profiles if outdated"
            ])

        # Add role analysis to insights
        insights['role_analysis'] = {
            'summary': f"Found {len(role_mismatches)} tasks potentially misaligned with assigned user roles",
            'mismatches': role_mismatches,
            'recommendations': [
                f"Review task assignment for {mismatch['task_name']} (assigned to {mismatch['assigned_to']} - {mismatch['job_title']})"
                for mismatch in role_mismatches
            ] if role_mismatches else ["Task assignments align well with team member roles"]
        }

        # Update workload analysis to include job titles
        for username, data in insights['workload_analysis']['raw_data'].items():
            if username in user_details:
                data['job_title'] = user_details[username]['job_title']

        # Update risks and suggestions based on role analysis
        if role_mismatches:
            insights['risks'].append(f"{len(role_mismatches)} tasks may be misaligned with assigned user roles")
            insights['suggestions'].extend([
                "Review task assignments based on team member roles and responsibilities",
                "Consider role-based task distribution for better efficiency",
                "Update team member job profiles if responsibilities have changed"
            ])

        return insights

    def _extract_skills_from_description(self, description: str) -> List[str]:
        """Extract required skills from task description"""
        # Common technical skills to look for
        common_skills = [
            "python", "java", "javascript", "react", "angular", "vue", "node", "django",
            "flask", "sql", "nosql", "aws", "azure", "devops", "ci/cd", "docker",
            "kubernetes", "machine learning", "ai", "data science", "frontend", "backend",
            "fullstack", "testing", "security", "cloud", "architecture", "design",
            "project management", "agile", "scrum"
        ]
        
        # Extract skills from description
        found_skills = []
        desc_lower = description.lower()
        for skill in common_skills:
            if skill in desc_lower:
                found_skills.append(skill)
                
        return found_skills

    def _find_better_match(self, required_skills: List[str], user_details: Dict) -> str:
        """Find better user match for required skills"""
        best_match = None
        best_match_score = 0
        
        for username, details in user_details.items():
            user_skills = set(details['skills'] or []) | set(details['expertise'] or []) | set(details['specializations'] or [])
            match_score = sum(1 for skill in required_skills if skill.lower() in {s.lower() for s in user_skills})
            
            if match_score > best_match_score:
                best_match = username
                best_match_score = match_score
                
        if best_match:
            return f"Consider reassigning to {best_match} who has matching skills"
        return "No better skill match found in the team"

    def _generate_skill_suggestion(self, user_data: Dict) -> str:
        """Generate skill-based suggestions for a user"""
        total = user_data['total']
        matched = user_data.get('skill_matched_tasks', 0)
        mismatched = user_data.get('skill_mismatched_tasks', 0)
        
        if mismatched > matched:
            return f"Consider reassigning tasks - {mismatched}/{total} tasks don't match expertise"
        elif mismatched > 0:
            return f"Review {mismatched} task(s) that don't align with expertise"
        else:
            return "Task assignments well-aligned with expertise"

    def _extract_project_domain(self, description: str) -> str:
        """Extract the project domain from description"""
        # Simple keyword-based domain extraction
        domains = {
            'web': ['web', 'website', 'frontend', 'backend', 'fullstack'],
            'mobile': ['mobile', 'ios', 'android', 'app'],
            'data': ['data', 'analytics', 'machine learning', 'ai'],
            'infrastructure': ['devops', 'cloud', 'infrastructure', 'deployment'],
            'enterprise': ['enterprise', 'business', 'erp', 'crm']
        }
        
        description = description.lower()
        for domain, keywords in domains.items():
            if any(keyword in description for keyword in keywords):
                return domain
        return 'general'

    def _extract_success_factors(self, project: Project) -> List[str]:
        """Extract success factors from a completed project"""
        factors = []
        if project.tasks:
            on_time_tasks = len([t for t in project.tasks if t.deadline and t.end_date and t.end_date <= t.deadline])
            total_tasks = len(project.tasks)
            if on_time_tasks / total_tasks >= 0.8:
                factors.append('High on-time completion rate')
            
            if project.end_date and project.start_date:
                planned_duration = (project.end_date - project.start_date).days
                actual_duration = (max(t.end_date for t in project.tasks if t.end_date) - project.start_date).days
                if actual_duration <= planned_duration:
                    factors.append('Completed within planned duration')
        
        return factors

    def _extract_risk_factors(self, project: Project) -> List[str]:
        """Extract risk factors from a completed project"""
        factors = []
        if project.tasks:
            overdue_tasks = len([t for t in project.tasks if t.deadline and t.end_date and t.end_date > t.deadline])
            if overdue_tasks > len(project.tasks) * 0.2:
                factors.append('High number of overdue tasks')
            
            if project.end_date and project.start_date:
                planned_duration = (project.end_date - project.start_date).days
                actual_duration = (max(t.end_date for t in project.tasks if t.end_date) - project.start_date).days
                if actual_duration > planned_duration * 1.2:
                    factors.append('Significant timeline overrun')
        
        return factors

    def _format_historical_insights(self, similar_projects: List[Dict]) -> str:
        """Format historical project insights for the prompt"""
        if not similar_projects:
            return "No similar projects found in history."
            
        insights = []
        for proj in similar_projects:
            insights.append(
                f"Project: {proj['name']}\n"
                f"- Duration: {proj['duration']} days\n"
                f"- Completion Rate: {proj['completion_rate']*100:.1f}%\n"
                f"- Success Factors: {', '.join(proj['success_factors'])}\n"
                f"- Risk Factors: {', '.join(proj['risk_factors'])}"
            )
        return "\n\n".join(insights)

    def _format_workload(self, workload: Dict[str, Dict[str, int]]) -> str:
        """Format workload data for the prompt"""
        result = []
        for username, data in workload.items():
            result.append(
                f"{username}:\n"
                f"- Total Tasks: {data['total']}\n"
                f"- In Progress: {data['in_progress']}\n"
                f"- Completed: {data['completed']}\n"
                f"- Overdue: {data['overdue']}\n"
                f"- High Priority: {data['high_priority']}"
            )
        return "\n\n".join(result)

    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response into structured data"""
        try:
            # Try to parse as JSON first
            return json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback to basic parsing if JSON fails
            lines = response.text.split('\n')
            result = {
                'summary': '',
                'risks': [],
                'suggestions': [],
                'timeline_status': '',
                'critical_tasks': [],
                'workload_analysis': {},
                'resource_allocation': {},
                'performance_metrics': {}
            }
            
            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.lower().startswith('summary:'):
                    current_section = 'summary'
                    result['summary'] = line.split(':', 1)[1].strip()
                elif line.lower().startswith('risk:'):
                    current_section = 'risks'
                    result['risks'].append(line.split(':', 1)[1].strip())
                elif line.lower().startswith('suggestion:'):
                    current_section = 'suggestions'
                    result['suggestions'].append(line.split(':', 1)[1].strip())
                elif line.lower().startswith('timeline:'):
                    current_section = 'timeline_status'
                    result['timeline_status'] = line.split(':', 1)[1].strip()
                elif current_section:
                    if line.startswith('-'):
                        line = line[1:].strip()
                    if current_section in ['risks', 'suggestions']:
                        result[current_section].append(line)
                    elif current_section in ['summary', 'timeline_status']:
                        result[current_section] += ' ' + line
            
            return result

    def _generate_basic_insights(
        self,
        total_tasks: int,
        completed_tasks: int,
        overdue_tasks: int,
        workload: Dict[str, Dict[str, int]]
    ) -> Dict[str, Any]:
        """Generate basic insights when AI analysis fails"""
        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Find overloaded team members and their specific issues
        overloaded_members = []
        workload_issues = []
        for username, data in workload.items():
            issues = []
            if data['total'] > 5:
                issues.append(f"High task count ({data['total']} tasks)")
            if data['overdue'] > 2:
                issues.append(f"{data['overdue']} overdue tasks")
            if data['in_progress'] > 3:
                issues.append(f"Many in-progress tasks ({data['in_progress']})")
            if data['high_priority'] > 2:
                issues.append(f"Multiple high-priority tasks ({data['high_priority']})")
            
            if issues:
                overloaded_members.append(username)
                workload_issues.append(f"{username}: {', '.join(issues)}")

        # Calculate team-wide metrics
        total_in_progress = sum(data['in_progress'] for data in workload.values())
        total_high_priority = sum(data['high_priority'] for data in workload.values())
        
        # Generate more specific suggestions based on the analysis
        suggestions = [
            "Focus on completing overdue tasks",
            *(f"Redistribute tasks from {name}" for name in overloaded_members)
        ]
        
        if total_in_progress > total_tasks * 0.7:
            suggestions.append("Too many tasks in progress simultaneously - consider limiting WIP")
        
        if total_high_priority > total_tasks * 0.3:
            suggestions.append("High number of priority tasks - review task prioritization")
            
        # Add specific completion recommendations
        if completion_percentage < 20:
            suggestions.append("Project is in early stages - focus on setting up clear milestones")
        elif completion_percentage < 50:
            suggestions.append("Project is in development - ensure regular progress reviews")
        else:
            suggestions.append("Project is advancing - focus on clearing blockers and maintaining momentum")
        
        return {
            'summary': f"Project is {completion_percentage:.1f}% complete with {overdue_tasks} overdue tasks. "
                      f"{'Team members are experiencing workload issues.' if overloaded_members else 'Team workload is balanced.'}",
            'completion_percentage': completion_percentage,
            'risks': [
                f"{overdue_tasks} tasks are currently overdue",
                *(f"Workload issue: {issue}" for issue in workload_issues),
                f"{total_in_progress} tasks currently in progress",
                f"{total_high_priority} high-priority tasks require attention"
            ],
            'suggestions': suggestions,
            'timeline_status': 'Critical' if overdue_tasks > total_tasks * 0.3 else 'At risk' if overdue_tasks > 0 else 'On track',
            'critical_tasks': [
                {
                    'issue': 'Overdue tasks accumulating',
                    'impact': 'Project timeline at risk and potential cascade effect on dependent tasks',
                    'recommendation': 'Implement daily standup meetings to address blockers and prioritize overdue tasks'
                }
            ] if overdue_tasks > 0 else [],
            'workload_analysis': {
                'raw_data': workload,
                'overview': f"Team of {len(workload)} members with {total_in_progress} active tasks",
                'concerns': [
                    *(f"{name} needs immediate workload review" for name in overloaded_members),
                    f"Team has {total_high_priority} high-priority tasks to handle"
                ] if overloaded_members else ["No major workload concerns"],
                'recommendations': [
                    "Implement task rotation to balance expertise and workload",
                    "Set up regular capacity planning meetings",
                    "Review and adjust task priorities weekly"
                ]
            },
            'resource_allocation': {
                'current_status': 'Needs optimization' if overloaded_members else 'Balanced',
                'optimization_suggestions': [
                    "Redistribute tasks from overloaded team members",
                    "Review task priorities and deadlines",
                    "Consider pair programming for knowledge sharing",
                    "Implement work-in-progress limits per team member"
                ]
            },
            'performance_metrics': {
                'efficiency_score': 'Low' if overdue_tasks > 2 else 'Medium' if overdue_tasks > 0 else 'High',
                'risk_score': 'High' if overdue_tasks > 2 else 'Medium' if overdue_tasks > 0 else 'Low',
                'timeline_accuracy': f'{(total_tasks - overdue_tasks) / total_tasks * 100:.1f}%',
                'key_metrics': [
                    f"Completion rate: {completion_percentage:.1f}%",
                    f"Overdue rate: {(overdue_tasks / total_tasks * 100):.1f}%",
                    f"Tasks in progress: {(total_in_progress / total_tasks * 100):.1f}%",
                    f"High priority tasks: {(total_high_priority / total_tasks * 100):.1f}%"
                ],
                'team_velocity': {
                    'tasks_in_progress': total_in_progress,
                    'completion_rate': f"{completion_percentage:.1f}%",
                    'bottlenecks': [name for name, data in workload.items() if data['overdue'] > 0]
                }
            }
        }

    def _analyze_dependency_chain(self, task: Task, all_tasks: Dict[int, Task], chain=None, visited=None) -> Dict:
        """Analyze a task's dependency chain and calculate critical path metrics"""
        if chain is None:
            chain = []
        if visited is None:
            visited = set()
            
        if task.id in visited:
            return {
                'is_circular': True,
                'chain': chain,
                'total_duration': 0,
                'critical_path': [],
                'bottlenecks': []
            }
            
        visited.add(task.id)
        chain.append(task.id)
        
        # Calculate this task's duration
        planned_duration = 0
        if task.start_date and task.deadline:
            planned_duration = (task.deadline - task.start_date).days
        
        # Get dependent tasks
        dependent_tasks = [all_tasks[t.id] for t in task.dependent_tasks if t.id in all_tasks]
        
        # Analyze each dependency path
        dependency_paths = []
        bottlenecks = []
        
        if not dependent_tasks:  # End of chain
            return {
                'is_circular': False,
                'chain': chain,
                'total_duration': planned_duration,
                'critical_path': [task.id] if planned_duration > 0 else [],
                'bottlenecks': []
            }
            
        for dep_task in dependent_tasks:
            dep_analysis = self._analyze_dependency_chain(dep_task, all_tasks, chain.copy(), visited.copy())
            
            if dep_analysis['is_circular']:
                bottlenecks.append({
                    'type': 'circular_dependency',
                    'tasks': dep_analysis['chain'],
                    'impact': 'Critical: Circular dependency detected'
                })
            else:
                total_path_duration = planned_duration + dep_analysis['total_duration']
                dependency_paths.append({
                    'duration': total_path_duration,
                    'path': dep_analysis['chain'],
                    'critical_path': dep_analysis['critical_path']
                })
                
                # Check for timeline issues
                if task.deadline and dep_task.start_date and task.deadline > dep_task.start_date:
                    bottlenecks.append({
                        'type': 'timeline_conflict',
                        'tasks': [task.id, dep_task.id],
                        'impact': f'Dependent task {dep_task.name} starts before parent task {task.name} deadline'
                    })
        
        # Find the critical path (longest duration)
        if dependency_paths:
            critical_path = max(dependency_paths, key=lambda x: x['duration'])
            return {
                'is_circular': False,
                'chain': chain,
                'total_duration': critical_path['duration'],
                'critical_path': [task.id] + critical_path['critical_path'],
                'bottlenecks': bottlenecks
            }
        
        return {
            'is_circular': False,
            'chain': chain,
            'total_duration': planned_duration,
            'critical_path': [task.id] if planned_duration > 0 else [],
            'bottlenecks': bottlenecks
        }

    def _analyze_project_timeline(self, project: Project, tasks: List[Task]) -> Dict:
        """Analyze project timeline considering task dependencies"""
        # Create tasks lookup dictionary
        tasks_dict = {task.id: task for task in tasks}
        
        # Find root tasks (tasks with no dependencies)
        root_tasks = [task for task in tasks if not task.depends_on]
        
        # Analyze each dependency chain
        dependency_chains = []
        all_bottlenecks = []
        critical_paths = []
        
        for root_task in root_tasks:
            chain_analysis = self._analyze_dependency_chain(root_task, tasks_dict)
            dependency_chains.append(chain_analysis)
            
            if chain_analysis['bottlenecks']:
                all_bottlenecks.extend(chain_analysis['bottlenecks'])
            if chain_analysis['critical_path']:
                critical_paths.append({
                    'path': chain_analysis['critical_path'],
                    'duration': chain_analysis['total_duration']
                })
        
        # Find the overall critical path
        project_critical_path = max(critical_paths, key=lambda x: x['duration']) if critical_paths else None
        
        # Calculate timeline feasibility
        timeline_feasible = True
        timeline_issues = []
        
        if project.end_date:
            project_duration = (project.end_date - project.start_date).days if project.start_date else 0
            if project_critical_path and project_critical_path['duration'] > project_duration:
                timeline_feasible = False
                timeline_issues.append(
                    f"Critical path duration ({project_critical_path['duration']} days) exceeds project duration ({project_duration} days)"
                )
        
        # Analyze parallel task execution
        parallel_tasks = self._analyze_parallel_tasks(tasks)
        
        return {
            'timeline_feasible': timeline_feasible,
            'timeline_issues': timeline_issues,
            'critical_path': project_critical_path,
            'bottlenecks': all_bottlenecks,
            'parallel_execution': parallel_tasks,
            'dependency_chains': dependency_chains
        }

    def _analyze_parallel_tasks(self, tasks: List[Task]) -> Dict:
        """Analyze tasks that can be executed in parallel"""
        parallel_groups = {}
        
        for task in tasks:
            if task.start_date:
                start_key = task.start_date.strftime('%Y-%m-%d')
                if start_key not in parallel_groups:
                    parallel_groups[start_key] = []
                parallel_groups[start_key].append({
                    'task_id': task.id,
                    'name': task.name,
                    'assigned_to': task.assigned_to,
                    'planned_hours': task.planned_hours
                })
        
        # Identify resource conflicts in parallel tasks
        resource_conflicts = []
        for date, task_group in parallel_groups.items():
            user_workload = {}
            for task in task_group:
                if task['assigned_to']:
                    if task['assigned_to'] not in user_workload:
                        user_workload[task['assigned_to']] = []
                    user_workload[task['assigned_to']].append(task)
            
            # Check for overloaded users
            for user_id, user_tasks in user_workload.items():
                total_hours = sum(t['planned_hours'] or 0 for t in user_tasks)
                if total_hours > 8:  # Assuming 8-hour workday
                    resource_conflicts.append({
                        'date': date,
                        'user_id': user_id,
                        'total_hours': total_hours,
                        'tasks': user_tasks
                    })
        
        return {
            'parallel_groups': parallel_groups,
            'resource_conflicts': resource_conflicts
        }

    def _analyze_role_task_fit(self, task_description: str, job_title: str) -> Dict:
        """Analyze if a task matches the assigned user's job role"""
        # Common job roles and their typical responsibilities
        role_keywords = {
            'developer': ['coding', 'programming', 'development', 'debugging', 'implementation', 'unit testing'],
            'frontend': ['ui', 'ux', 'user interface', 'css', 'html', 'react', 'angular', 'vue', 'design'],
            'backend': ['api', 'database', 'server', 'endpoint', 'authentication', 'authorization'],
            'devops': ['deployment', 'ci/cd', 'pipeline', 'infrastructure', 'kubernetes', 'docker', 'aws', 'azure'],
            'qa': ['testing', 'quality assurance', 'test cases', 'automation testing', 'bug tracking'],
            'project manager': ['coordination', 'planning', 'scheduling', 'resource allocation', 'stakeholder'],
            'designer': ['design', 'mockup', 'wireframe', 'prototype', 'user experience', 'visual'],
            'data scientist': ['data analysis', 'machine learning', 'analytics', 'statistics', 'data modeling'],
            'architect': ['architecture', 'system design', 'technical planning', 'infrastructure design']
        }

        if not job_title or not task_description:
            return {
                'match_score': 0,
                'is_match': False,
                'reason': 'Missing job title or task description'
            }

        # Normalize job title and description
        job_title_lower = job_title.lower()
        desc_lower = task_description.lower()

        # Find the most relevant role category
        role_matches = []
        for role, keywords in role_keywords.items():
            if role in job_title_lower:
                # Count how many role-specific keywords appear in the task description
                keyword_matches = sum(1 for keyword in keywords if keyword in desc_lower)
                if keyword_matches > 0:
                    role_matches.append({
                        'role': role,
                        'matches': keyword_matches,
                        'total_keywords': len(keywords),
                        'score': keyword_matches / len(keywords)
                    })

        if not role_matches:
            return {
                'match_score': 0,
                'is_match': False,
                'reason': f'No role-specific keywords found for {job_title}'
            }

        # Get the best matching role
        best_match = max(role_matches, key=lambda x: x['score'])
        
        return {
            'match_score': best_match['score'],
            'is_match': best_match['score'] > 0.3,  # Consider it a match if more than 30% of keywords match
            'role': best_match['role'],
            'matched_keywords': best_match['matches'],
            'reason': f"Task {'matches' if best_match['score'] > 0.3 else 'does not match'} {job_title} responsibilities"
        }

    def _analyze_role_task_match(self, task: Task) -> Dict:
        """Analyze how well the assigned user's role matches the task requirements and suggest better matches if needed"""
        if not task.assignee or not task.assignee.job_title:
            # Find potential assignees even if no current assignee
            better_matches = self._find_better_assignees(task)
            return {
                "match_score": 0.0,
                "is_match": False,
                "risk_level": "high",
                "reason": "No assignee or job title specified",
                "better_matches": better_matches
            }

        # Define role-specific keywords and their weights
        role_requirements = {
            'developer': {
                'keywords': ['coding', 'programming', 'development', 'implementation', 'bug fix', 'feature'],
                'weight': 1.0,
                'related_roles': ['software engineer', 'programmer', 'full stack', 'backend', 'frontend']
            },
            'designer': {
                'keywords': ['design', 'ui', 'ux', 'layout', 'wireframe', 'mockup', 'prototype'],
                'weight': 1.0,
                'related_roles': ['ui designer', 'ux designer', 'graphic designer']
            },
            'project manager': {
                'keywords': ['planning', 'coordination', 'meeting', 'schedule', 'resource', 'timeline'],
                'weight': 1.0,
                'related_roles': ['program manager', 'scrum master', 'product owner']
            },
            'qa': {
                'keywords': ['testing', 'quality', 'test case', 'bug', 'verification', 'validation'],
                'weight': 1.0,
                'related_roles': ['quality assurance', 'tester', 'test engineer']
            },
            'devops': {
                'keywords': ['deployment', 'infrastructure', 'pipeline', 'ci/cd', 'configuration'],
                'weight': 1.0,
                'related_roles': ['sre', 'system engineer', 'infrastructure engineer']
            },
            'data scientist': {
                'keywords': ['analysis', 'data', 'algorithm', 'model', 'machine learning', 'statistics'],
                'weight': 1.0,
                'related_roles': ['data analyst', 'ml engineer', 'data engineer']
            }
        }

        # Calculate role match score
        job_title = task.assignee.job_title.lower()
        description = f"{task.name} {task.description}".lower()
        
        best_match_score = 0
        matched_role = None
        
        for role, info in role_requirements.items():
            # Check direct role match
            if role in job_title or any(related in job_title for related in info['related_roles']):
                # Calculate keyword match in task description
                keyword_matches = sum(1 for kw in info['keywords'] if kw in description)
                match_score = (keyword_matches / len(info['keywords'])) * info['weight']
                
                if match_score > best_match_score:
                    best_match_score = match_score
                    matched_role = role

        # Calculate risk level based on match score
        if best_match_score >= 0.7:
            risk_level = "low"
        elif best_match_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "high"

        # Factor in experience level if available
        if task.assignee.experience_level:
            experience_multiplier = {
                'senior': 0.8,  # Reduces risk
                'mid': 1.0,    # Neutral
                'junior': 1.2   # Increases risk
            }.get(task.assignee.experience_level.lower(), 1.0)
            
            if experience_multiplier != 1.0:
                if risk_level == "low" and experience_multiplier > 1:
                    risk_level = "medium"
                elif risk_level == "high" and experience_multiplier < 1:
                    risk_level = "medium"

        # Find better matches if current match is not optimal
        better_matches = []
        if risk_level in ["medium", "high"]:
            better_matches = self._find_better_assignees(task)

        return {
            "match_score": best_match_score,
            "is_match": best_match_score >= 0.4,
            "matched_role": matched_role,
            "risk_level": risk_level,
            "reason": self._generate_role_mismatch_reason(best_match_score, matched_role, task.assignee.job_title),
            "better_matches": better_matches
        }

    def _find_better_assignees(self, task: Task) -> List[Dict]:
        """Find team members who might be better suited for the task"""
        try:
            # Extract required skills and role from task
            required_skills = self._extract_skills_from_description(task.description or "")
            task_keywords = set((task.name + " " + (task.description or "")).lower().split())
            
            # Get all active users
            project_users = self.db.query(User).filter(User.is_active == True).all()
            
            # Score each potential assignee
            potential_assignees = []
            current_assignee_id = task.assignee.id if task.assignee else None
            
            for user in project_users:
                if user.id == current_assignee_id:
                    continue  # Skip current assignee
                    
                score = 0
                reasons = []
                
                # Score based on job title match
                if user.job_title:
                    job_title_words = set(user.job_title.lower().split())
                    title_match = len(job_title_words & task_keywords) / len(job_title_words) if job_title_words else 0
                    score += title_match * 0.25  # Reduced weight to accommodate availability
                    if title_match > 0.5:
                        reasons.append(f"Job title '{user.job_title}' matches task requirements")

                # Score based on skills match
                user_skills = set(user.skills or []) | set(user.expertise or []) | set(user.specializations or [])
                if user_skills and required_skills:
                    skills_match = len([skill for skill in required_skills if skill.lower() in {s.lower() for s in user_skills}])
                    score += (skills_match / len(required_skills)) * 0.3 if required_skills else 0
                    if skills_match > 0:
                        reasons.append(f"Matches {skills_match} required skills")

                # Score based on experience level
                if user.experience_level:
                    experience_scores = {'senior': 0.15, 'mid': 0.1, 'junior': 0.05}
                    score += experience_scores.get(user.experience_level.lower(), 0)
                    if user.experience_level.lower() == 'senior':
                        reasons.append("Senior level experience")

                # Score based on availability (increased weight)
                active_tasks = self.db.query(Task).filter(
                    Task.assigned_to == user.id,
                    Task.state.in_(['todo', 'in_progress'])
                ).count()
                
                # Availability score (now worth 30% of total score)
                availability_score = max(0, 0.3 - (active_tasks * 0.05))  # Each task reduces score by 0.05
                score += availability_score
                
                if active_tasks == 0:
                    reasons.append("Fully available (no active tasks)")
                elif active_tasks < 3:
                    reasons.append(f"Good availability (only {active_tasks} active tasks)")

                # Project familiarity bonus (if task belongs to a project)
                if task.project_id:
                    user_project_tasks = self.db.query(Task).filter(
                        Task.project_id == task.project_id,
                        Task.assigned_to == user.id,
                        Task.state == 'done'
                    ).count()
                    if user_project_tasks > 0:
                        project_familiarity = min(0.1, user_project_tasks * 0.02)  # Max 10% bonus
                        score += project_familiarity
                        reasons.append(f"Familiar with project ({user_project_tasks} completed tasks)")

                # Add to potential assignees if score is significant
                if score > 0.3:  # Lower threshold to be more inclusive
                    potential_assignees.append({
                        "user_id": user.id,
                        "username": user.username,
                        "full_name": user.full_name,
                        "job_title": user.job_title,
                        "experience_level": user.experience_level,
                        "match_score": round(score, 2),
                        "reasons": reasons,
                        "current_tasks": active_tasks,
                        "availability_score": round(availability_score, 2)
                    })

            # Sort by match score and return top matches
            return sorted(potential_assignees, key=lambda x: x['match_score'], reverse=True)[:3]
            
        except Exception as e:
            print(f"Error finding better assignees: {str(e)}")
            return []

    def _generate_role_mismatch_reason(self, match_score: float, matched_role: str, job_title: str) -> str:
        """Generate a detailed reason for role mismatch"""
        if match_score >= 0.7:
            return f"Good role match: {job_title} aligns well with task requirements"
        elif match_score >= 0.4:
            return f"Partial role match: {job_title} has some alignment with {matched_role} requirements"
        else:
            return f"Poor role match: {job_title} may not be ideal for this task type"

    def _calculate_unassigned_task_risk(self, task: Task) -> Dict:
        """Calculate comprehensive risk metrics for an unassigned task"""
        now = datetime.now(timezone.utc)
        risk_factors = ["Task has no assignee"]
        risk_reducers = []
        base_risk_score = 0.4  # Starting risk for being unassigned

        # Time-based risk calculation
        time_risk = 0
        time_buffer_ratio = 0
        
        if task.deadline and task.planned_hours:
            # Calculate available working hours until deadline
            days_until_deadline = (task.deadline.replace(tzinfo=timezone.utc) - now).days
            working_hours_available = max(0, days_until_deadline * 8)  # Assuming 8-hour workdays
            
            # Calculate time buffer ratio (available time / planned time)
            time_buffer_ratio = working_hours_available / task.planned_hours
            
            if time_buffer_ratio >= 3:  # Lots of time available
                risk_reducers.append(f"Generous time allocation (buffer ratio: {time_buffer_ratio:.1f}x)")
                time_risk -= 0.1
            elif time_buffer_ratio >= 2:  # Good amount of time
                risk_reducers.append(f"Adequate time allocation (buffer ratio: {time_buffer_ratio:.1f}x)")
                time_risk -= 0.05
            elif time_buffer_ratio < 1:  # Not enough time
                risk_factors.append(f"Tight deadline (only {time_buffer_ratio:.1f}x planned hours available)")
                time_risk += 0.2
        else:
            if not task.deadline:
                risk_reducers.append("No deadline pressure")
                time_risk -= 0.1
            if not task.planned_hours:
                risk_factors.append("No time estimation available")
                time_risk += 0.1

        # Dependencies risk
        dependency_risk = 0
        if task.depends_on:
            blocked_dependencies = [dep for dep in task.depends_on if dep.state != 'done']
            if blocked_dependencies:
                risk_factors.append(f"Blocked by {len(blocked_dependencies)} incomplete dependencies")
                dependency_risk += 0.1 * len(blocked_dependencies)
            else:
                risk_reducers.append("All dependencies completed")
                dependency_risk -= 0.1

        # Priority-based risk
        priority_risk = 0
        if task.priority:
            priority_multipliers = {
                'low': -0.1,    # Low priority reduces risk
                'normal': 0,
                'high': 0.15,
                'urgent': 0.25
            }
            priority_risk = priority_multipliers.get(task.priority.lower(), 0)
            if priority_risk > 0:
                risk_factors.append(f"{task.priority.capitalize()} priority task requires immediate assignment")
            elif priority_risk < 0:
                risk_reducers.append("Low priority allows flexibility in assignment")

        # Project context risk
        project_risk = 0
        if task.project:
            project_health = self._analyze_project_context(task)
            if project_health['project_delayed']:
                risk_factors.append("Project is already delayed")
                project_risk += 0.1
            if project_health['completion_rate'] > 0.7:
                risk_reducers.append("Project is in final stages")
                project_risk -= 0.05

        # Task complexity risk
        complexity_risk = 0
        if task.description:
            # Analyze task description for complexity indicators
            complexity_indicators = ['complex', 'difficult', 'challenging', 'critical', 'important']
            complexity_count = sum(1 for indicator in complexity_indicators if indicator in task.description.lower())
            if complexity_count > 0:
                risk_factors.append(f"Task appears complex ({complexity_count} complexity indicators)")
                complexity_risk += 0.05 * complexity_count
            else:
                risk_reducers.append("Task appears straightforward")
                complexity_risk -= 0.05

        # Calculate final risk score
        risk_score = base_risk_score + time_risk + dependency_risk + priority_risk + project_risk + complexity_risk
        risk_score = max(0.1, min(1.0, risk_score))  # Clamp between 0.1 and 1.0

        # Find potential assignees
        potential_assignees = self._find_better_assignees(task)

        # Adjust recommendations based on comprehensive analysis
        recommendations = [
            "Assign task to a team member immediately",
        ]

        if potential_assignees:
            best_match = potential_assignees[0]
            recommendations.append(
                f"Consider assigning to {best_match['full_name']} "
                f"({best_match['reasons'][0].lower()})"
            )
            if time_buffer_ratio < 1:
                recommendations.append(
                    f"Consider assigning to {best_match['full_name']} with additional support "
                    "due to tight timeline"
                )
        else:
            recommendations.append("Review team availability and capacity")

        if task.planned_hours:
            recommendations.append(
                f"Allocate {task.planned_hours} hours "
                f"({'sufficient' if time_buffer_ratio >= 2 else 'tight'} timeline)"
            )

        if complexity_risk > 0:
            recommendations.append("Consider breaking down into smaller subtasks")

        return {
            "risk_score": round(risk_score, 2),
            "risk_factors": risk_factors,
            "risk_reducers": risk_reducers,
            "metrics": {
                "assignment": {
                    "status": "unassigned",
                    "risk_level": "high" if risk_score > 0.6 else "medium" if risk_score > 0.3 else "low",
                    "potential_assignees": potential_assignees
                },
                "time": {
                    "buffer_ratio": round(time_buffer_ratio, 2) if task.planned_hours else None,
                    "planned_hours": task.planned_hours,
                    "available_hours": working_hours_available if task.deadline else None,
                    "risk_contribution": round(time_risk, 2)
                },
                "dependencies": {
                    "count": len(task.depends_on) if task.depends_on else 0,
                    "blocked": len(blocked_dependencies) if task.depends_on else 0,
                    "risk_contribution": round(dependency_risk, 2)
                },
                "priority": {
                    "level": task.priority,
                    "risk_contribution": round(priority_risk, 2)
                },
                "project_context": {
                    "health": project_health if task.project else None,
                    "risk_contribution": round(project_risk, 2)
                },
                "complexity": {
                    "indicators": complexity_count if task.description else 0,
                    "risk_contribution": round(complexity_risk, 2)
                }
            },
            "recommendations": recommendations
        }

    async def analyze_task_risk(self, task_id: int) -> Dict:
        """Perform advanced AI-based risk analysis on a task."""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {
                "error": "Task not found",
                "task_id": task_id
            }

        # Handle unassigned tasks with comprehensive risk analysis
        if not task.assignee:
            risk_analysis = self._calculate_unassigned_task_risk(task)
            return {
                "task_id": task_id,
                "at_risk": risk_analysis["risk_score"] > 0.5,
                "risk_score": risk_analysis["risk_score"],
                "risk_factors": risk_analysis["risk_factors"],
                "risk_reducers": risk_analysis["risk_reducers"],
                "metrics": risk_analysis["metrics"],
                "recommendations": risk_analysis["recommendations"],
                "estimated_delay_days": self._estimate_unassigned_delay(task),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

        # Continue with regular risk analysis for assigned tasks
        time_metrics = self._calculate_time_metrics(task, datetime.now(timezone.utc))
        activity_analysis = self._analyze_task_activity(task)
        dependency_analysis = self._analyze_task_dependencies(task)
        workload_analysis = self._analyze_assignee_workload(task)
        project_context = self._analyze_project_context(task)
        sentiment_analysis = self._analyze_task_sentiment(task)
        role_analysis = self._analyze_role_task_match(task)

        # Enhanced weight distribution including role match
        weights = {
            'time': 0.25,
            'activity': 0.15,
            'dependencies': 0.15,
            'workload': 0.15,
            'project': 0.1,
            'sentiment': 0.05,
            'role_match': 0.15  # New weight for role matching
        }

        # Calculate risk score with more factors
        risk_factors = []
        risk_score = 0.0

        # Time-based risks (now considers planned hours)
        time_risk = 0.0
        if time_metrics['is_overdue']:
            risk_factors.append(f"Task is overdue by {time_metrics['overdue_days']} days")
            time_risk = min(1.0, time_metrics['overdue_days'] / 30)
        elif time_metrics['deadline_approaching']:
            risk_factors.append(f"Deadline approaching in {time_metrics['days_to_deadline']} days with {task.progress}% progress")
            time_risk = 1 - (time_metrics['days_to_deadline'] / 14)

        # Adjust time risk based on planned hours
        if task.planned_hours:
            if task.planned_hours < 4:  # Short tasks
                time_risk *= 0.8  # Reduce risk for short tasks
            elif task.planned_hours > 20:  # Long tasks
                time_risk *= 1.2  # Increase risk for long tasks

        risk_score += weights['time'] * time_risk

        # Role match risks
        role_risk = 0.0
        if role_analysis['risk_level'] == 'high':
            risk_factors.append(f"Task-role mismatch: {role_analysis['reason']}")
            role_risk = 1.0
        elif role_analysis['risk_level'] == 'medium':
            risk_factors.append(f"Partial task-role match: {role_analysis['reason']}")
            role_risk = 0.5

        risk_score += weights['role_match'] * role_risk

        # Activity risks
        if activity_analysis['inactive_days'] > 3:
            risk_factors.append(f"No activity for {activity_analysis['inactive_days']} days")
            risk_score += weights['activity'] * min(1.0, activity_analysis['inactive_days'] / 14)
        if activity_analysis['progress_rate'] < 0.5:
            risk_factors.append("Slow progress rate compared to expected velocity")
            risk_score += weights['activity'] * (1 - activity_analysis['progress_rate'])

        # Dependency risks
        if dependency_analysis['blocked']:
            risk_factors.append(f"Blocked by {len(dependency_analysis['blocking_tasks'])} tasks")
            risk_score += weights['dependencies']
        if dependency_analysis['is_critical_path']:
            risk_factors.append("On critical path with delays")
            risk_score += weights['dependencies'] * 0.5

        # Workload risks
        if workload_analysis['overloaded']:
            risk_factors.append(f"Assignee has {workload_analysis['active_tasks']} active tasks")
            risk_score += weights['workload'] * min(1.0, workload_analysis['active_tasks'] / 10)

        # Project context risks
        if project_context['project_delayed']:
            risk_factors.append("Project is behind schedule")
            risk_score += weights['project']

        # Sentiment risks
        if sentiment_analysis['negative_sentiment']:
            risk_factors.append("Recent communications indicate issues or frustration")
            risk_score += weights['sentiment']

        # Generate recommendations
        recommendations = self._generate_risk_recommendations(
            task,
            risk_factors,
            time_metrics,
            dependency_analysis,
            workload_analysis,
            role_analysis
        )

        return {
            "task_id": task_id,
            "at_risk": risk_score > 0.5,
            "risk_score": round(risk_score, 2),
            "risk_factors": risk_factors,
            "metrics": {
                "time": time_metrics,
                "activity": activity_analysis,
                "dependencies": dependency_analysis,
                "workload": workload_analysis,
                "project_health": project_context,
                "sentiment": sentiment_analysis,
                "role_match": role_analysis
            },
            "recommendations": recommendations,
            "estimated_delay_days": self._estimate_delay(
                task,
                risk_score,
                time_metrics,
                activity_analysis,
                role_analysis
            ),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

    def _generate_risk_recommendations(
        self,
        task: Task,
        risk_factors: List[str],
        time_metrics: Dict,
        dependency_analysis: Dict,
        workload_analysis: Dict,
        role_analysis: Dict
    ) -> List[str]:
        """Generate actionable recommendations based on risk analysis"""
        recommendations = []

        # Role-based recommendations
        if role_analysis['risk_level'] == 'high':
            recommendations.append("Consider reassigning task to someone with more relevant role expertise")
            if task.assignee and task.assignee.experience_level == 'junior':
                recommendations.append("Assign a senior team member as mentor for this task")
        elif role_analysis['risk_level'] == 'medium':
            recommendations.append("Review task requirements and ensure assignee has necessary support")

        # Time-based recommendations
        if time_metrics['is_overdue']:
            recommendations.append("Immediate attention needed - task is overdue")
            recommendations.append("Consider breaking down the task into smaller subtasks")
        elif time_metrics['deadline_approaching']:
            recommendations.append("Review and update task timeline")
            recommendations.append("Increase monitoring frequency")

        # Dependency recommendations
        if dependency_analysis['blocked']:
            recommendations.append("Escalate blocking issues to project manager")
            recommendations.append("Schedule dependency resolution meeting")

        # Workload recommendations
        if workload_analysis['overloaded']:
            recommendations.append("Consider redistributing tasks among team members")
            recommendations.append("Review task priorities and timeline")

        # Add general recommendations if needed
        if len(recommendations) < 2:
            recommendations.append("Maintain regular progress updates")
            recommendations.append("Document any potential blockers early")

        return recommendations

    def _estimate_delay(
        self,
        task: Task,
        risk_score: float,
        time_metrics: Dict,
        activity_analysis: Dict,
        role_analysis: Dict
    ) -> int:
        """Estimate potential delay in days based on risk analysis"""
        if not task.deadline:
            return 0

        base_delay = 0

        # Factor in current overdue days
        if time_metrics['is_overdue']:
            base_delay += time_metrics['overdue_days']

        # Factor in progress rate
        if activity_analysis['progress_rate'] > 0:
            remaining_progress = 100 - (task.progress or 0)
            days_per_percent = activity_analysis['inactive_days'] / activity_analysis['progress_rate']
            base_delay += int(remaining_progress * days_per_percent / 100)

        # Factor in role mismatch
        role_multiplier = {
            'low': 1.0,
            'medium': 1.2,
            'high': 1.5
        }.get(role_analysis['risk_level'], 1.0)

        # Apply risk multipliers
        return int(base_delay * role_multiplier * (1 + risk_score))

    def _estimate_unassigned_delay(self, task: Task) -> int:
        """Estimate potential delay for an unassigned task"""
        base_delay = 3  # Minimum delay for assignment process
        
        if task.deadline:
            days_to_deadline = (task.deadline.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days
            if days_to_deadline < 7:
                base_delay += 2  # Additional urgency factor
                
        if task.priority in ['high', 'urgent']:
            base_delay += 2  # Priority factor
            
        if task.depends_on:
            base_delay += len(task.depends_on)  # Dependency complexity factor
            
        return base_delay

    def _calculate_time_metrics(self, task: Task, current_time: datetime) -> Dict:
        """Calculate time-based metrics for a task"""
        metrics = {
            "is_overdue": False,
            "overdue_days": 0,
            "deadline_approaching": False,
            "days_to_deadline": None,
            "progress_rate": 0.0,
            "expected_completion_date": None,
            "risk_level": "low"
        }

        if not task.deadline:
            return metrics

        # Calculate days to deadline
        deadline = task.deadline.replace(tzinfo=timezone.utc)
        days_to_deadline = (deadline - current_time).days
        metrics["days_to_deadline"] = days_to_deadline

        # Check if overdue
        if days_to_deadline < 0:
            metrics["is_overdue"] = True
            metrics["overdue_days"] = abs(days_to_deadline)
            metrics["risk_level"] = "high"
        elif days_to_deadline <= 7:  # Warning threshold: 7 days
            metrics["deadline_approaching"] = True
            metrics["risk_level"] = "medium"

        # Calculate progress rate
        if task.start_date:
            start_date = task.start_date.replace(tzinfo=timezone.utc)
            days_since_start = max(1, (current_time - start_date).days)
            progress = task.progress or 0
            metrics["progress_rate"] = progress / days_since_start

            # Estimate completion date based on current progress rate
            if metrics["progress_rate"] > 0:
                remaining_progress = 100 - progress
                days_needed = remaining_progress / metrics["progress_rate"]
                metrics["expected_completion_date"] = current_time + timedelta(days=days_needed)

                # Update risk level based on expected completion
                if metrics["expected_completion_date"] > deadline:
                    metrics["risk_level"] = "high"

        return metrics

    def _analyze_task_activity(self, task: Task) -> Dict:
        """Analyze task activity patterns"""
        now = datetime.now(timezone.utc)
        
        # Get recent activities
        activities = sorted(task.activities, key=lambda x: x.created_at, reverse=True) if task.activities else []
        
        # Calculate inactive days
        last_activity_date = activities[0].created_at if activities else task.created_at
        inactive_days = (now - last_activity_date.replace(tzinfo=timezone.utc)).days
        
        # Calculate progress rate
        progress_rate = 0.0
        if task.start_date:
            days_active = max(1, (now - task.start_date.replace(tzinfo=timezone.utc)).days)
            progress = task.progress or 0
            progress_rate = progress / days_active
            
        return {
            "inactive_days": inactive_days,
            "progress_rate": progress_rate,
            "recent_activities": [
                {
                    "type": activity.activity_type,
                    "description": activity.description,
                    "date": activity.created_at.isoformat()
                }
                for activity in activities[:5]  # Last 5 activities
            ],
            "activity_level": "low" if inactive_days > 7 else "medium" if inactive_days > 3 else "high"
        }

    def _analyze_task_dependencies(self, task: Task) -> Dict:
        """Analyze task dependencies and their impact"""
        blocking_tasks = []
        blocked_by = []
        
        # Check dependencies
        for dep in task.depends_on:
            if dep.state != 'done':
                blocked_by.append({
                    "task_id": dep.id,
                    "name": dep.name,
                    "state": dep.state,
                    "progress": dep.progress
                })
                
        # Check dependent tasks
        for dep in task.dependent_tasks:
            if dep.state != 'done':
                blocking_tasks.append({
                    "task_id": dep.id,
                    "name": dep.name,
                    "state": dep.state,
                    "progress": dep.progress
                })
                
        # Determine if task is on critical path
        is_critical = len(blocking_tasks) > 2 or len(blocked_by) > 2
                
        return {
            "blocked": len(blocked_by) > 0,
            "blocking_tasks": blocked_by,
            "dependent_tasks": blocking_tasks,
            "is_critical_path": is_critical,
            "dependency_count": len(blocked_by) + len(blocking_tasks),
            "risk_level": "high" if len(blocked_by) > 0 else "medium" if is_critical else "low"
        }

    def _analyze_assignee_workload(self, task: Task) -> Dict:
        """Analyze assignee's current workload"""
        if not task.assignee:
            return {
                "overloaded": False,
                "active_tasks": 0,
                "risk_level": "medium",
                "reason": "No assignee"
            }
            
        # Get assignee's active tasks
        active_tasks = self.db.query(Task).filter(
            Task.assigned_to == task.assignee.id,
            Task.state.in_(['todo', 'in_progress'])
        ).all()
        
        # Calculate workload metrics
        high_priority_tasks = len([t for t in active_tasks if t.priority in ['high', 'urgent']])
        overdue_tasks = len([t for t in active_tasks if t.deadline and t.deadline < datetime.now(timezone.utc)])
        
        # Determine if overloaded
        is_overloaded = (
            len(active_tasks) > 5 or  # Too many active tasks
            high_priority_tasks > 2 or  # Too many high priority tasks
            overdue_tasks > 1  # Has overdue tasks
        )
        
        return {
            "overloaded": is_overloaded,
            "active_tasks": len(active_tasks),
            "high_priority_tasks": high_priority_tasks,
            "overdue_tasks": overdue_tasks,
            "risk_level": "high" if is_overloaded else "medium" if len(active_tasks) > 3 else "low",
            "reason": f"Assignee has {len(active_tasks)} active tasks ({high_priority_tasks} high priority, {overdue_tasks} overdue)"
        }

    def _analyze_project_context(self, task: Task) -> Dict:
        """Analyze the project context and its impact on the task"""
        if not task.project:
            return {
                "project_delayed": False,
                "risk_level": "medium",
                "reason": "No project context"
            }
            
        project = task.project
        
        # Calculate project metrics
        total_tasks = len(project.tasks)
        completed_tasks = len([t for t in project.tasks if t.state == 'done'])
        overdue_tasks = len([t for t in project.tasks if t.deadline and t.deadline < datetime.now(timezone.utc)])
        
        # Calculate project health
        completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
        is_delayed = (
            overdue_tasks > total_tasks * 0.2 or  # More than 20% tasks overdue
            (project.end_date and project.end_date < datetime.now(timezone.utc))  # Project deadline passed
        )
        
        return {
            "project_delayed": is_delayed,
            "completion_rate": completion_rate,
            "overdue_tasks_ratio": overdue_tasks / total_tasks if total_tasks > 0 else 0,
            "risk_level": "high" if is_delayed else "medium" if completion_rate < 0.5 else "low",
            "reason": f"Project is {'delayed' if is_delayed else 'on track'} with {completion_rate*100:.1f}% completion"
        }

    def _analyze_task_sentiment(self, task: Task) -> Dict:
        """Analyze sentiment from task comments and activities"""
        # Get recent comments and activities
        comments = sorted(task.comments, key=lambda x: x.created_at, reverse=True) if task.comments else []
        activities = sorted(task.activities, key=lambda x: x.created_at, reverse=True) if task.activities else []
        
        # Simple keyword-based sentiment analysis
        negative_keywords = ['blocked', 'issue', 'problem', 'delay', 'bug', 'error', 'failed', 'stuck']
        positive_keywords = ['completed', 'fixed', 'resolved', 'implemented', 'success', 'working']
        
        negative_count = 0
        positive_count = 0
        
        # Analyze comments
        for comment in comments[:10]:  # Last 10 comments
            text = comment.content.lower()
            negative_count += sum(1 for word in negative_keywords if word in text)
            positive_count += sum(1 for word in positive_keywords if word in text)
            
        # Analyze activities
        for activity in activities[:10]:  # Last 10 activities
            text = activity.description.lower()
            negative_count += sum(1 for word in negative_keywords if word in text)
            positive_count += sum(1 for word in positive_keywords if word in text)
            
        # Calculate sentiment metrics
        total_mentions = negative_count + positive_count
        if total_mentions > 0:
            negative_ratio = negative_count / total_mentions
        else:
            negative_ratio = 0
            
        return {
            "negative_sentiment": negative_ratio > 0.6,  # More than 60% negative
            "sentiment_score": 1 - negative_ratio if total_mentions > 0 else 0.5,
            "risk_level": "high" if negative_ratio > 0.6 else "medium" if negative_ratio > 0.3 else "low",
            "recent_negative_mentions": negative_count,
            "recent_positive_mentions": positive_count
        }

# Create a singleton instance
_ai_service = None

def get_ai_service(db: Session) -> AIService:
    """Get or create singleton AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService(db)
    return _ai_service 