from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TaskEnvironment(str, Enum):
    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    HYBRID = "hybrid"

class WeatherImpact(BaseModel):
    temperature: float
    humidity: float
    precipitation_probability: float
    wind_speed: float
    weather_condition: str
    impact_score: float
    analysis: str

class ComplexityFactors(BaseModel):
    technical_complexity: float = Field(..., ge=0, le=100)
    scope_complexity: float = Field(..., ge=0, le=100)
    time_pressure: float = Field(..., ge=0, le=100)
    environmental_complexity: float = Field(..., ge=0, le=100)
    dependencies_impact: float = Field(..., ge=0, le=100)

class TaskComplexityAnalysis(BaseModel):
    task_id: int
    environment_type: TaskEnvironment
    total_score: float = Field(..., ge=0, le=100)
    factors: ComplexityFactors
    weather_impact: Optional[WeatherImpact] = None
    analysis_summary: str
    last_updated: datetime
    confidence_score: float = Field(..., ge=0, le=1)

class TaskComplexityResponse(BaseModel):
    success: bool
    complexity: TaskComplexityAnalysis
    message: Optional[str] = None 