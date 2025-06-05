from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from models.task import Task, TaskState
from services.complexity_service import ComplexityService
from services.ai_service import AIService
from enum import Enum
from services.redis_service import get_redis_client
import logging

logger = logging.getLogger(__name__)

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
        self.redis = get_redis_client()
        self.CACHE_EXPIRATION = timedelta(minutes=30)  # Cache for 30 minutes

    async def calculate_priority(self, task_id: int) -> Dict:
        """
        Calculate task priority using rules first, then AI if needed.
        Returns both rule-based and AI suggestions along with final priority.
        """
        # Try to get from cache first
        cache_key = f"task_priority:{task_id}"
        try:
            cached_priority = self.redis.get(cache_key)
            if cached_priority:
                logger.debug(f"Cache hit for task {task_id}")
                return cached_priority
        except Exception as e:
            logger.warning(f"Error accessing Redis cache for task {task_id}: {str(e)}")

        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # If priority is manually set, respect it
        if hasattr(task, 'priority_source') and task.priority_source == PrioritySource.MANUAL:
            result = {
                "task_id": task_id,
                "final_priority": task.priority.lower(),
                "priority_source": PrioritySource.MANUAL,
                "rule_priority": None,
                "ai_priority": None,
                "confidence": 1.0,
                "reasoning": ["Priority manually set by user"],
                "deadline_factor": self._calculate_deadline_factor(task)
            }
            # Try to cache manual priority
            try:
                self.redis.setex(
                    cache_key,
                    int(self.CACHE_EXPIRATION.total_seconds()),
                    result
                )
            except Exception as e:
                logger.warning(f"Error caching priority for task {task_id}: {str(e)}")
            return result

        # 1. Apply rule-based logic first
        rule_priority, rule_confidence, rule_reasoning = await self._apply_priority_rules(task)

        # 2. If rule confidence is low, use AI
        ai_priority = None
        ai_reasoning = []
        if rule_confidence < 0.8:
            try:
                ai_result = await self._get_ai_priority_suggestion(task)
                ai_priority = ai_result["priority"]
                ai_reasoning = ai_result["reasoning"]
            except Exception as e:
                logger.error(f"Error getting AI priority suggestion for task {task_id}: {str(e)}")

        # 3. Determine final priority
        final_priority = ai_priority if (rule_confidence < 0.8 and ai_priority) else rule_priority
        
        # 4. Calculate deadline factor
        deadline_factor = self._calculate_deadline_factor(task)

        result = {
            "task_id": task_id,
            "final_priority": final_priority.lower(),
            "priority_source": PrioritySource.AI if ai_priority else PrioritySource.RULE,
            "rule_priority": rule_priority.lower() if rule_priority else None,
            "ai_priority": ai_priority.lower() if ai_priority else None,
            "confidence": 1.0 if ai_priority else rule_confidence,
            "reasoning": ai_reasoning if ai_priority else rule_reasoning,
            "deadline_factor": deadline_factor
        }

        # Try to cache the result
        try:
            self.redis.setex(
                cache_key,
                int(self.CACHE_EXPIRATION.total_seconds()),
                result
            )
        except Exception as e:
            logger.warning(f"Error caching priority for task {task_id}: {str(e)}")
        
        return result

    def _calculate_deadline_factor(self, task: Task) -> float:
        """Calculate urgency factor based on deadline proximity"""
        if not task.deadline:
            return 0.0

        now = datetime.now(timezone.utc)
        time_until_deadline = task.deadline - now

        if time_until_deadline.total_seconds() <= 0:
            return 1.0  # Past deadline
        
        # Convert to days
        days_until_deadline = time_until_deadline.total_seconds() / (24 * 3600)
        
        if days_until_deadline <= 1:  # 1 day or less
            return 1.0
        elif days_until_deadline <= 3:  # 3 days or less
            return 0.8
        elif days_until_deadline <= 7:  # 1 week or less
            return 0.6
        elif days_until_deadline <= 14:  # 2 weeks or less
            return 0.4
        elif days_until_deadline <= 30:  # 1 month or less
            return 0.2
        else:
            return 0.0

    def invalidate_cache(self, task_id: int) -> None:
        """Invalidate the cached priority for a task"""
        try:
            cache_key = f"task_priority:{task_id}"
            self.redis.delete(cache_key)
        except Exception as e:
            logger.warning(f"Error invalidating cache for task {task_id}: {str(e)}")

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

    async def analyze_and_rank_tasks(self, tasks: List[Task]) -> List[Dict]:
        """
        Use AI to analyze and rank a list of tasks based on various factors.
        Returns tasks with detailed analysis and ranking scores.
        """
        ranked_tasks = []
        
        for task in tasks:
            # Try to get cached analysis first
            cache_key = f"task_analysis:{task.id}"
            cached_analysis = self.redis.get(cache_key)
            
            if cached_analysis:
                ranked_tasks.append(cached_analysis)
                continue

            # Prepare task context for AI analysis
            context = await self._prepare_task_context(task)
            
            try:
                # Get AI analysis
                analysis = await self.ai_service.analyze_task_urgency(
                    task_id=task.id,
                    context=context
                )
                
                task_analysis = {
                    "task_id": task.id,
                    "name": task.name,
                    "urgency_score": analysis.get("urgency_score", 0.5),
                    "impact_score": analysis.get("impact_score", 0.5),
                    "complexity_score": context["complexity_score"],
                    "deadline_factor": self._calculate_deadline_factor(task),
                    "blocking_factor": len(task.dependent_tasks) / 10,  # Normalize to 0-1
                    "analysis_reasoning": analysis.get("reasoning", []),
                    "suggested_order": analysis.get("suggested_order", 0),
                    "task": task
                }

                # Calculate final ranking score
                task_analysis["final_score"] = self._calculate_ranking_score(task_analysis)
                
                # Cache the analysis
                try:
                    self.redis.setex(
                        cache_key,
                        int(self.CACHE_EXPIRATION.total_seconds()),
                        task_analysis
                    )
                except Exception as e:
                    logger.warning(f"Error caching task analysis for task {task.id}: {str(e)}")
                
                ranked_tasks.append(task_analysis)
                
            except Exception as e:
                logger.error(f"Error analyzing task {task.id}: {str(e)}")
                # Add task with basic scoring if AI analysis fails
                ranked_tasks.append(self._create_fallback_analysis(task))

        # Sort tasks by final score
        return sorted(ranked_tasks, key=lambda x: x["final_score"], reverse=True)

    async def _prepare_task_context(self, task: Task) -> Dict:
        """Prepare comprehensive context for AI analysis"""
        try:
            complexity = await self.complexity_service.analyze_task_complexity(self.db, task.id)
            complexity_score = complexity.total_score / 100  # Normalize to 0-1
        except Exception:
            complexity_score = 0.5  # Default to medium complexity

        return {
            "description": task.description,
            "deadline": task.deadline,
            "complexity_score": complexity_score,
            "dependencies": [
                {
                    "id": dep.id,
                    "name": dep.name,
                    "state": dep.state
                } for dep in task.depends_on
            ],
            "dependent_tasks": [
                {
                    "id": dep.id,
                    "name": dep.name,
                    "state": dep.state
                } for dep in task.dependent_tasks
            ],
            "project_urgency": task.project.urgency_score if task.project else 0.5,
            "created_at": task.created_at,
            "last_updated": task.updated_at,
            "state": task.state,
            "assigned_to": task.assigned_to
        }

    def _calculate_ranking_score(self, analysis: Dict) -> float:
        """Calculate final ranking score using weighted factors"""
        weights = {
            "urgency": 0.3,
            "impact": 0.2,
            "deadline": 0.2,
            "complexity": 0.15,
            "blocking": 0.15
        }

        score = (
            analysis["urgency_score"] * weights["urgency"] +
            analysis["impact_score"] * weights["impact"] +
            analysis["deadline_factor"] * weights["deadline"] +
            analysis["complexity_score"] * weights["complexity"] +
            analysis["blocking_factor"] * weights["blocking"]
        )

        return min(max(score, 0.0), 1.0)

    def _create_fallback_analysis(self, task: Task) -> Dict:
        """Create basic analysis when AI analysis fails"""
        deadline_factor = self._calculate_deadline_factor(task)
        blocking_factor = len(task.dependent_tasks) / 10  # Normalize to 0-1

        return {
            "task_id": task.id,
            "name": task.name,
            "urgency_score": 0.7,  # Default high urgency for urgent tasks
            "impact_score": 0.5,  # Default medium impact
            "complexity_score": 0.5,  # Default medium complexity
            "deadline_factor": deadline_factor,
            "blocking_factor": blocking_factor,
            "analysis_reasoning": ["Basic analysis due to AI analysis failure"],
            "suggested_order": 0,
            "final_score": (0.7 + 0.5 + deadline_factor + blocking_factor) / 4,
            "task": task
        } 