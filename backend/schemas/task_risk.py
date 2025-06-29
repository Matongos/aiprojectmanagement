from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class TaskRiskAnalysisResponse(BaseModel):
    """Response schema for task risk analysis"""
    task_id: int
    analysis_timestamp: datetime
    risk_score: float = Field(..., ge=0, le=100)
    risk_level: str  # 'minimal', 'low', 'medium', 'high', 'critical', 'extreme'
    
    # Component scores
    time_sensitivity: float = Field(..., ge=0, le=30)
    complexity: float = Field(..., ge=0, le=20)
    priority: float = Field(..., ge=0, le=20)
    role_match: float = Field(..., ge=0, le=20)
    dependencies: float = Field(..., ge=0, le=10)
    comments: float = Field(..., ge=0, le=10)
    
    # Detailed analysis
    risk_factors: Dict[str, Any]
    recommendations: Dict[str, Any]
    metrics: Optional[Dict[str, Any]] = None
    
    # Analysis metadata
    analysis_version: str = "1.0"
    calculation_method: str = "weighted_component_analysis"
    
    class Config:
        from_attributes = True

class TaskRiskHistoryResponse(BaseModel):
    """Response schema for task risk history"""
    task_id: int
    history: List[TaskRiskAnalysisResponse]
    total_analyses: int
    average_risk_score: float
    risk_trend: str  # 'increasing', 'decreasing', 'stable'
    
    class Config:
        from_attributes = True

class ProjectRiskSummaryResponse(BaseModel):
    """Response schema for project risk summary"""
    project_id: int
    total_tasks: int
    analyzed_tasks: int
    average_risk_score: float
    risk_distribution: Dict[str, int]  # risk_level -> count
    high_risk_tasks: List[Dict[str, Any]]
    recommendations: List[str]
    
    class Config:
        from_attributes = True 