from typing import Dict, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models.task import Task, TaskState
from services.complexity_service import ComplexityService
from services.ai_service import AIService
from enum import Enum

class PrioritySource(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
    RULE = "rule"
    AI = "ai"

class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class PriorityService:
    def __init__(self, db: Session):
        self.db = db
        self.complexity_service = ComplexityService()
        self.ai_service = AIService(db)

    async def calculate_priority(self, task_id: int) -> Dict:
        """
        Calculate task priority using rules first, then AI if needed.
        Returns both rule-based and AI suggestions along with final priority.
        """
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # If priority is manually set, respect it
        if hasattr(task, 'priority_source') and task.priority_source == PrioritySource.MANUAL:
            return {
                "task_id": task_id,
                "final_priority": task.priority.lower(),
                "priority_source": PrioritySource.MANUAL,
                "rule_priority": None,
                "ai_priority": None,
                "confidence": 1.0,
                "reasoning": ["Priority manually set by user"]
            }

        # 1. Apply rule-based logic first
        rule_priority, rule_confidence, rule_reasoning = await self._apply_priority_rules(task)

        # 2. If rule confidence is low, use AI
        ai_priority = None
        ai_reasoning = []
        if rule_confidence < 0.8:
            ai_result = await self._get_ai_priority_suggestion(task)
            ai_priority = ai_result["priority"]
            ai_reasoning = ai_result["reasoning"]

        # 3. Determine final priority
        final_priority = ai_priority if (rule_confidence < 0.8 and ai_priority) else rule_priority
        
        return {
            "task_id": task_id,
            "final_priority": final_priority.lower(),
            "priority_source": PrioritySource.AI if ai_priority else PrioritySource.RULE,
            "rule_priority": rule_priority.lower() if rule_priority else None,
            "ai_priority": ai_priority.lower() if ai_priority else None,
            "confidence": 1.0 if ai_priority else rule_confidence,
            "reasoning": ai_reasoning if ai_priority else rule_reasoning
        }

    async def _apply_priority_rules(self, task: Task) -> tuple[TaskPriority, float, List[str]]:
        """Apply rule-based logic to determine priority"""
        now = datetime.now(timezone.utc)
        reasoning = []
        
        # Get task complexity
        try:
            complexity_analysis = await self.complexity_service.analyze_task_complexity(self.db, task.id)
            complexity_score = complexity_analysis.total_score
        except Exception:
            complexity_score = 50  # Default to medium complexity

        # Check deadline
        if task.deadline:
            time_to_deadline = (task.deadline - now).total_seconds()
            
            # Less than 24 hours
            if time_to_deadline < 86400:
                reasoning.append("Deadline within 24 hours")
                return TaskPriority.URGENT, 1.0, reasoning
            
            # Less than 3 days
            if time_to_deadline < 3 * 86400:
                reasoning.append("Deadline within 3 days")
                return TaskPriority.HIGH, 0.9, reasoning

        # Check complexity and allocated time
        if complexity_score >= 80 and (task.planned_hours or 0) >= 24:
            reasoning.append("High complexity task with significant time allocation")
            return TaskPriority.HIGH, 0.85, reasoning

        # Check dependencies
        blocking_tasks = len([t for t in task.dependent_tasks if t.state != TaskState.DONE])
        if blocking_tasks > 0:
            reasoning.append(f"Task is blocking {blocking_tasks} other tasks")
            return TaskPriority.HIGH, 0.8, reasoning

        # Low complexity, no deadline
        if not task.deadline and complexity_score < 30:
            reasoning.append("Low complexity task without deadline")
            return TaskPriority.LOW, 0.7, reasoning

        # Default case - need AI input
        reasoning.append("No clear priority rules matched")
        return TaskPriority.NORMAL, 0.5, reasoning

    async def _get_ai_priority_suggestion(self, task: Task) -> Dict:
        """Get priority suggestion from AI service"""
        try:
            # Get project urgency if available
            project_urgency = task.project.urgency_score if task.project else 0.5

            # Prepare context for AI
            context = {
                "description": task.description,
                "deadline": str(task.deadline) if task.deadline else None,
                "complexity_score": task.metrics.complexity_score if task.metrics else None,
                "dependency_count": len(task.depends_on),
                "is_blocking": len(task.dependent_tasks) > 0,
                "project_urgency": project_urgency
            }

            # Get AI suggestion
            suggestion = await self.ai_service.suggest_task_priority(task.id)
            
            return {
                "priority": suggestion["suggested_priority"].lower(),
                "confidence": suggestion.get("priority_score", 0.7),
                "reasoning": suggestion.get("reasoning", ["AI-based priority suggestion"])
            }
        except Exception as e:
            print(f"Error getting AI priority suggestion: {str(e)}")
            return {
                "priority": TaskPriority.NORMAL,
                "confidence": 0.5,
                "reasoning": ["Failed to get AI suggestion, using default priority"]
            } 