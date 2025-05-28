from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import json
from zoneinfo import ZoneInfo

from services.ollama_service import get_ollama_client
from services.vector_service import VectorService
from models.task import Task
from models.project import Project
from models.time_entry import TimeEntry

class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.ollama_client = get_ollama_client()
        self.vector_service = VectorService(db)
        
    async def analyze_task(self, task_id: int) -> Dict:
        """Analyze a task and provide AI insights"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {}
            
        # Prepare comprehensive task context
        context = {
            # Basic Task Info
            "name": task.name,
            "description": task.description,
            "priority": task.priority,
            "state": task.state,
            "progress": task.progress,
            "planned_hours": task.planned_hours,
            
            # Dates
            "start_date": task.start_date.isoformat() if task.start_date else None,
            "end_date": task.end_date.isoformat() if task.end_date else None,
            "deadline": task.deadline.isoformat() if task.deadline else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "date_last_stage_update": task.date_last_stage_update.isoformat() if task.date_last_stage_update else None,
            
            # Stage Information
            "stage": {
                "name": task.stage.name if task.stage else None,
                "sequence": task.stage.sequence if task.stage else None,
                "description": task.stage.description if task.stage else None
            },
            
            # Project Context
            "project": {
                "name": task.project.name if task.project else None,
                "description": task.project.description if task.project else None
            },
            
            # Assignee Information
            "assignee": {
                "id": task.assignee.id if task.assignee else None,
                "username": task.assignee.username if task.assignee else None,
                "full_name": task.assignee.full_name if task.assignee else None
            },
            
            # Dependencies and Relationships
            "parent_task": {
                "name": task.parent.name if task.parent else None,
                "state": task.parent.state if task.parent else None
            },
            "subtask_count": len(task.subtasks) if task.subtasks else 0,
            "depends_on_count": len(task.depends_on) if task.depends_on else 0,
            "dependent_tasks_count": len(task.dependent_tasks) if task.dependent_tasks else 0,
            
            # Communication & Collaboration
            "comment_count": len(task.comments) if task.comments else 0,
            "latest_comments": [
                {
                    "content": comment.content,
                    "created_at": comment.created_at.isoformat()
                }
                for comment in task.comments[-3:] if task.comments
            ],
            
            # Time Tracking
            "time_entries": [
                {
                    "duration": entry.duration,
                    "description": entry.description,
                    "activity_type": entry.activity_type,
                    "is_billable": entry.is_billable,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None
                }
                for entry in task.time_entries[-5:] if task.time_entries
            ],
            "total_time_spent": sum(entry.duration for entry in task.time_entries) if task.time_entries else 0,
            
            # Tags and Categorization
            "tags": [tag.name for tag in task.tags] if task.tags else [],
            
            # Activity History
            "activity_count": len(task.activities) if task.activities else 0,
            "recent_activities": [
                {
                    "activity_type": activity.activity_type,
                    "description": activity.description,
                    "created_at": activity.created_at.isoformat()
                }
                for activity in task.activities[-5:] if task.activities
            ]
        }
        
        # Get similar tasks for comparison
        similar_tasks = await self.vector_service.find_similar(
            text=f"{task.name} {task.description}",
            entity_type="task",
            limit=5
        )
        
        # Prepare prompt for analysis
        prompt = f"""
        Analyze this task and provide insights in the following JSON format:
        {{
            "complexity": <integer between 1-10>,
            "risk_factors": [<list of risk factors as strings>],
            "time_accuracy": <float between 0-1>,
            "suggestions": [<list of suggestions as strings>],
            "patterns": {{
                "type": "<task type>",
                "common_issues": [<list of common issues>],
                "success_factors": [<list of success factors>]
            }}
        }}

        Task Details:
        Basic Information:
        - Name: {task.name}
        - Description: {task.description}
        - Priority: {task.priority}
        - State: {task.state}
        - Progress: {task.progress}%
        - Planned Hours: {task.planned_hours}
        
        Dates:
        - Created: {context['created_at']}
        - Start Date: {context['start_date']}
        - End Date: {context['end_date']}
        - Deadline: {context['deadline']}
        - Last Stage Update: {context['date_last_stage_update']}
        
        Stage & Project:
        - Current Stage: {context['stage']['name']}
        - Stage Sequence: {context['stage']['sequence']}
        - Project: {context['project']['name']}
        
        Assignee:
        - Name: {context['assignee']['full_name']}
        
        Dependencies:
        - Parent Task: {context['parent_task']['name']}
        - Subtasks: {context['subtask_count']}
        - Dependencies: {context['depends_on_count']}
        - Dependent Tasks: {context['dependent_tasks_count']}
        
        Communication:
        - Comments: {context['comment_count']}
        - Recent Comments: {[c['content'] for c in context['latest_comments']]}
        
        Time Tracking:
        - Total Time Spent: {context['total_time_spent']} hours
        - Recent Time Entries: {[f"{e['duration']}h: {e['description']}" for e in context['time_entries']]}
        
        Tags: {context['tags']}
        
        Activity:
        - Total Activities: {context['activity_count']}
        - Recent Activities: {[f"{a['activity_type']}: {a['description']}" for a in context['recent_activities']]}
        """
        
        # Get AI analysis
        response = await self.ollama_client.generate(
            model="codellama",
            prompt=prompt,
            stream=False
        )
        
        try:
            # Parse the response
            result = json.loads(response.text)
            
            # Ensure the response matches our expected format
            return {
                "complexity": int(result.get("complexity", 5)),
                "risk_factors": list(result.get("risk_factors", [])),
                "time_accuracy": float(result.get("time_accuracy", 0.5)),
                "suggestions": list(result.get("suggestions", [])),
                "patterns": result.get("patterns", {
                    "type": "unknown",
                    "common_issues": [],
                    "success_factors": []
                })
            }
        except Exception as e:
            print(f"Error parsing AI response: {str(e)}")
            # Return default values if parsing fails
            return {
                "complexity": 5,
                "risk_factors": ["Unable to analyze risks"],
                "time_accuracy": 0.5,
                "suggestions": ["Retry analysis"],
                "patterns": {
                    "type": "unknown",
                    "common_issues": [],
                    "success_factors": []
                }
            }
    
    async def suggest_task_priority(self, task_id: int) -> str:
        """Suggest priority for a task based on its characteristics"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return "normal"
            
        prompt = f"""
        Suggest priority for this task:
        
        Task Details:
        - Name: {task.name}
        - Description: {task.description}
        - Deadline: {task.deadline.isoformat() if task.deadline else 'None'}
        - Dependencies: {len(task.depends_on)}
        
        Return only one of: low, normal, high, urgent
        """
        
        response = await self.ollama_client.generate(
            model="codellama",
            prompt=prompt,
            stream=False
        )
        
        try:
            result = json.loads(response.text)
            return result.get("priority", "normal")
        except:
            return "normal"
    
    async def estimate_completion_time(self, task_id: int) -> float:
        """Estimate task completion time based on similar tasks"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return 0.0
            
        # Get similar completed tasks
        similar_tasks = await self.vector_service.find_similar(
            text=f"{task.name} {task.description}",
            entity_type="task",
            limit=10
        )
        
        if not similar_tasks:
            return task.planned_hours or 0.0
            
        # Calculate average completion time of similar tasks
        total_time = 0.0
        count = 0
        
        for task_id, _ in similar_tasks:
            similar = self.db.query(Task).get(task_id)
            if similar and similar.state == "done":
                actual_time = sum(entry.duration for entry in similar.time_entries)
                if actual_time > 0:
                    total_time += actual_time
                    count += 1
        
        return (total_time / count) if count > 0 else (task.planned_hours or 0.0)
    
    async def analyze_project_risks(self, project_id: int) -> Dict:
        """Analyze project risks using AI"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {}
            
        # Get project tasks
        tasks = project.tasks
        
        # Get current time with timezone
        current_time = datetime.now(ZoneInfo("UTC"))
        
        # Prepare project context
        context = {
            "name": project.name,
            "description": project.description,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
            "progress": project.progress,
            "task_count": len(tasks),
            "overdue_tasks": sum(1 for t in tasks if t.deadline and t.deadline < current_time),
            "high_priority_tasks": sum(1 for t in tasks if t.priority in ["high", "urgent"])
        }
        
        prompt = f"""
        Analyze project risks and provide detailed insights in JSON format:
        
        Project Details:
        - Name: {project.name}
        - Description: {project.description}
        - Progress: {project.progress}%
        - Total Tasks: {len(tasks)}
        - Overdue Tasks: {context['overdue_tasks']}
        - High Priority Tasks: {context['high_priority_tasks']}
        - Start Date: {context['start_date']}
        - End Date: {context['end_date']}
        
        Task Details:
        {[{
            'name': t.name,
            'state': t.state,
            'priority': t.priority,
            'progress': t.progress,
            'deadline': t.deadline.isoformat() if t.deadline else None
        } for t in tasks[:5]]}
        
        Please analyze and provide:
        1. Risk Level (1-10, where 10 is highest risk)
        2. Key Risk Factors (list specific issues that could impact project success)
        3. Mitigation Strategies (specific actions to address each risk factor)
        4. Timeline Assessment (on_track, at_risk, delayed, or critical)
        5. Resource Recommendations (specific suggestions for resource allocation)
        
        Return the analysis in this exact JSON format:
        {{
            "risk_level": "integer 1-10",
            "risk_factors": ["list of detailed risk descriptions"],
            "mitigations": ["list of specific mitigation strategies"],
            "timeline_status": "status string (on_track/at_risk/delayed/critical)",
            "resource_recommendations": ["list of specific resource suggestions"]
        }}
        
        Be specific and actionable in your analysis.
        """
        
        try:
            response = await self.ollama_client.generate(
                model="codellama",
                prompt=prompt,
                stream=False
            )
            
            result = json.loads(response.text)
            
            # Ensure we have valid data structure
            return {
                "risk_level": int(result.get("risk_level", 5)),
                "risk_factors": list(result.get("risk_factors", ["No risk factors identified"])),
                "mitigations": list(result.get("mitigations", ["No mitigation strategies provided"])),
                "timeline_status": str(result.get("timeline_status", "unknown")),
                "resource_recommendations": list(result.get("resource_recommendations", ["No resource recommendations provided"]))
            }
        except Exception as e:
            print(f"Error in project risk analysis: {str(e)}")
            return {
                "risk_level": 5,
                "risk_factors": ["Analysis error occurred"],
                "mitigations": ["Retry analysis"],
                "timeline_status": "unknown",
                "resource_recommendations": ["Unable to provide recommendations"]
            }

# Create a singleton instance
_ai_service = None

def get_ai_service(db: Session) -> AIService:
    """Get or create singleton AI service instance"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService(db)
    return _ai_service 