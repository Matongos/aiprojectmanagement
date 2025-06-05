"""Service for calculating task priority scores using AI"""
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from models.task import Task
from services.ai_service import AIService
import logging

logger = logging.getLogger(__name__)

class PriorityScoringService:
    def __init__(self, db: Session):
        self.db = db
        self.ai_service = AIService(db)

    async def calculate_priority_score(self, task: Task) -> float:
        """
        Calculate a priority score (0-100) for a task based on its attributes.
        Uses AI to analyze task content and determine importance.
        
        The score is calculated considering:
        - Task name and description content analysis
        - Current priority level
        - Priority reasoning
        - Task characteristics
        
        Returns:
            float: Priority score between 0 and 100
        """
        try:
            # Prepare task context for AI analysis
            context = {
                "task_name": task.name,
                "description": task.description or "",
                "priority_level": task.priority,
                "priority_reasoning": task.priority_reasoning or [],
                "deadline": str(task.deadline) if task.deadline else None,
                "state": task.state,
                "is_blocking": len(task.dependent_tasks) > 0
            }

            # Get AI analysis for priority score
            analysis = await self.ai_service.analyze_content(
                content_type="task_priority",
                content=context,
                analysis_prompt="""
                Analyze this task and assign a priority score from 0 to 100 based on:
                1. Task name and description importance (40% weight)
                2. Current priority level (30% weight)
                3. Priority reasoning validity (20% weight)
                4. Task characteristics (10% weight)
                
                Consider:
                - Higher scores for tasks with urgent/critical keywords
                - Impact on project/business
                - Dependencies and blocking status
                - Deadline proximity if present
                
                Return a JSON with:
                {
                    "score": float,  # 0-100
                    "score_breakdown": {
                        "content_score": float,  # 0-40
                        "priority_level_score": float,  # 0-30
                        "reasoning_score": float,  # 0-20
                        "characteristics_score": float  # 0-10
                    },
                    "explanation": string
                }
                """
            )

            # Extract and validate score
            score = float(analysis.get("score", 50.0))
            return min(max(score, 0.0), 100.0)  # Ensure score is between 0 and 100

        except Exception as e:
            logger.error(f"Error calculating priority score for task {task.id}: {str(e)}")
            # Return a default middle score in case of error
            return 50.0

    def _analyze_task_content(self, name: str, description: str) -> float:
        """Analyze task name and description for importance indicators"""
        # This is a fallback if AI service fails
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

    def _get_priority_level_score(self, priority: str) -> float:
        """Convert priority level to score component"""
        priority_scores = {
            'urgent': 30.0,
            'high': 22.5,
            'normal': 15.0,
            'low': 7.5
        }
        return priority_scores.get(priority.lower(), 15.0)

    def _evaluate_reasoning(self, reasoning: List[str]) -> float:
        """Evaluate priority reasoning for validity and strength"""
        if not reasoning:
            return 10.0  # Default middle score
            
        # Basic scoring based on number and length of reasons
        score = min(len(reasoning) * 5, 20.0)  # Up to 20 points
        
        return score 