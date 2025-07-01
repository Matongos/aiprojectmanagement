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
        Calculate a priority score for a task based only on:
        - risk_score (50%) from /ai/task/{task_id}/risk/stored
        - complexity_score (50%) from /task-complexity/stored/{task_id}
        Returns:
            float: Priority score (can exceed 100 if risk_score is high)
        """
        import httpx
        risk_score = 0.0
        complexity_score = 0.0
        try:
            # Fetch risk_score
            async with httpx.AsyncClient() as client:
                risk_resp = await client.get(f"http://localhost:8003/ai/task/{task.id}/risk/stored")
                if risk_resp.status_code == 200:
                    risk_data = risk_resp.json()
                    risk_score = float(risk_data.get("risk_score", 0.0))
                else:
                    risk_score = 0.0
                # Fetch complexity_score
                comp_resp = await client.get(f"http://localhost:8003/task-complexity/stored/{task.id}")
                if comp_resp.status_code == 200:
                    comp_data = comp_resp.json()
                    complexity_score = float(comp_data.get("complexity_score", 0.0))
                else:
                    complexity_score = 0.0
        except Exception as e:
            logger.error(f"Error fetching risk or complexity for task {task.id}: {str(e)}")
            risk_score = 0.0
            complexity_score = 0.0
        # Calculate final score (no capping)
        final_score = (risk_score * 0.5) + (complexity_score * 0.5)
        # Optionally, you can round for display
        return final_score

    async def calculate_priority_score_with_breakdown(self, task: Task) -> dict:
        """
        Same as calculate_priority_score, but returns breakdown and explanation.
        """
        import httpx
        risk_score = 0.0
        complexity_score = 0.0
        try:
            async with httpx.AsyncClient() as client:
                risk_resp = await client.get(f"http://localhost:8003/ai/task/{task.id}/risk/stored")
                if risk_resp.status_code == 200:
                    risk_data = risk_resp.json()
                    risk_score = float(risk_data.get("risk_score", 0.0))
                else:
                    risk_score = 0.0
                comp_resp = await client.get(f"http://localhost:8003/task-complexity/stored/{task.id}")
                if comp_resp.status_code == 200:
                    comp_data = comp_resp.json()
                    complexity_score = float(comp_data.get("complexity_score", 0.0))
                else:
                    complexity_score = 0.0
        except Exception as e:
            logger.error(f"Error fetching risk or complexity for task {task.id}: {str(e)}")
            risk_score = 0.0
            complexity_score = 0.0
        final_score = (risk_score * 0.5) + (complexity_score * 0.5)
        return {
            "score": final_score,
            "score_breakdown": {
                "risk_score_component": risk_score,
                "complexity_score_component": complexity_score
            },
            "explanation": "Priority score is a 50/50 weighted sum of risk score and complexity score (no capping)."
        }

    def _analyze_task_content(self, name: str, description: str) -> float:
        """Analyze task name and description for importance indicators (max 40, but will be scaled to 20)"""
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
        return min(score, 40.0)

    def _get_priority_level_score(self, priority: str) -> float:
        """Convert priority level to score component (max 30)"""
        priority_scores = {
            'urgent': 30.0,
            'high': 22.5,
            'normal': 15.0,
            'low': 7.5
        }
        return priority_scores.get(priority.lower(), 15.0) 