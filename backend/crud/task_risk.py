from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from models.task_risk import TaskRisk
from models.task import Task

class TaskRiskCRUD:
    def __init__(self, db: Session):
        self.db = db

    def create_risk_analysis(
        self,
        task_id: int,
        risk_score: float,
        risk_level: str,
        time_sensitivity: float,
        complexity: float,
        priority: float,
        risk_factors: Optional[Dict[str, Any]] = None,
        recommendations: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> TaskRisk:
        """Create a new risk analysis record for a task"""
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"Creating risk analysis for task {task_id}")
            logger.info(f"Risk score: {risk_score}, Level: {risk_level}")
            logger.info(f"Components: time={time_sensitivity}, complexity={complexity}, priority={priority}")
            
            risk_analysis = TaskRisk(
                task_id=task_id,
                risk_score=risk_score,
                risk_level=risk_level,
                time_sensitivity=time_sensitivity,
                complexity=complexity,
                priority=priority,
                risk_factors=risk_factors,
                recommendations=recommendations,
                metrics=metrics
            )
            
            self.db.add(risk_analysis)
            self.db.commit()
            self.db.refresh(risk_analysis)
            
            logger.info(f"Successfully created risk analysis with ID: {risk_analysis.id}")
            return risk_analysis
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creating risk analysis: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.db.rollback()
            raise

    def get_latest_risk_analysis(self, task_id: int) -> Optional[TaskRisk]:
        """Get the most recent risk analysis for a task"""
        return self.db.query(TaskRisk).filter(
            TaskRisk.task_id == task_id
        ).order_by(desc(TaskRisk.created_at)).first()

    def get_risk_analysis_history(
        self,
        task_id: int,
        days: int = 7
    ) -> List[TaskRisk]:
        """Get risk analysis history for a task within specified days"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        return self.db.query(TaskRisk).filter(
            TaskRisk.task_id == task_id,
            TaskRisk.created_at >= cutoff_date
        ).order_by(desc(TaskRisk.created_at)).all()

    def get_project_risk_analyses(self, project_id: int) -> List[TaskRisk]:
        """Get all risk analyses for tasks in a project"""
        return self.db.query(TaskRisk).join(Task).filter(
            Task.project_id == project_id
        ).order_by(desc(TaskRisk.created_at)).all()

    def update_risk_analysis(
        self,
        risk_id: int,
        risk_score: float,
        risk_level: str,
        time_sensitivity: float,
        complexity: float,
        priority: float,
        risk_factors: Optional[Dict[str, Any]] = None,
        recommendations: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> Optional[TaskRisk]:
        """Update an existing risk analysis record"""
        risk_analysis = self.db.query(TaskRisk).filter(TaskRisk.id == risk_id).first()
        if not risk_analysis:
            return None
            
        risk_analysis.risk_score = risk_score
        risk_analysis.risk_level = risk_level
        risk_analysis.time_sensitivity = time_sensitivity
        risk_analysis.complexity = complexity
        risk_analysis.priority = priority
        risk_analysis.risk_factors = risk_factors
        risk_analysis.recommendations = recommendations
        risk_analysis.metrics = metrics
        
        self.db.commit()
        self.db.refresh(risk_analysis)
        return risk_analysis

    def delete_risk_analysis(self, risk_id: int) -> bool:
        """Delete a risk analysis record"""
        risk_analysis = self.db.query(TaskRisk).filter(TaskRisk.id == risk_id).first()
        if not risk_analysis:
            return False
            
        self.db.delete(risk_analysis)
        self.db.commit()
        return True

    def get_high_risk_tasks(self, threshold: float = 0.7) -> List[TaskRisk]:
        """Get all tasks with risk scores above the threshold"""
        return self.db.query(TaskRisk).filter(
            TaskRisk.risk_score >= threshold
        ).order_by(desc(TaskRisk.risk_score)).all()

    def get_risk_statistics(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """Get risk statistics for tasks or a specific project"""
        query = self.db.query(TaskRisk)
        
        if project_id:
            query = query.join(Task).filter(Task.project_id == project_id)
        
        risk_analyses = query.all()
        
        if not risk_analyses:
            return {
                "total_analyses": 0,
                "average_risk_score": 0,
                "risk_distribution": {"low": 0, "medium": 0, "high": 0, "critical": 0, "extreme": 0},
                "highest_risk_score": 0,
                "lowest_risk_score": 0
            }
        
        risk_scores = [ra.risk_score for ra in risk_analyses]
        risk_levels = [ra.risk_level for ra in risk_analyses]
        
        return {
            "total_analyses": len(risk_analyses),
            "average_risk_score": sum(risk_scores) / len(risk_scores),
            "risk_distribution": {
                "low": risk_levels.count("low"),
                "medium": risk_levels.count("medium"),
                "high": risk_levels.count("high"),
                "critical": risk_levels.count("critical"),
                "extreme": risk_levels.count("extreme")
            },
            "highest_risk_score": max(risk_scores),
            "lowest_risk_score": min(risk_scores)
        } 