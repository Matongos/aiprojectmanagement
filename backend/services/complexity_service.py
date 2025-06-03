from typing import Optional, Dict, Any
from datetime import datetime, timezone
import json
import requests
from sqlalchemy.orm import Session
from models.task import Task
from schemas.task_complexity import (
    TaskComplexityAnalysis,
    TaskEnvironment,
    ComplexityFactors,
    WeatherImpact
)
from services.weather_service import get_weather_service
from services.weather_cache_service import get_weather_cache_service
from config import settings

class ComplexityService:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.weather_service = get_weather_service()
        self.weather_cache = get_weather_cache_service()

    async def analyze_task_complexity(self, db: Session, task_id: int) -> TaskComplexityAnalysis:
        """Calculate the complexity score for a task"""
        # Get task details
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")

        # 1. Analyze task text using AI
        text_analysis = await self._analyze_task_text(task.name, task.description)
        
        # 2. Determine task environment and location
        environment_type = await self._classify_task_environment(task.name, task.description)
        location = self.weather_service.extract_location_from_text(f"{task.name} {task.description}")
        
        # 3. Calculate time pressure
        time_pressure = self._calculate_time_pressure(task)
        
        # 4. Get weather impact if outdoor task
        weather_impact = None
        if environment_type in [TaskEnvironment.OUTDOOR, TaskEnvironment.HYBRID]:
            weather_impact = await self._get_weather_impact(task, location)

        # 5. Calculate complexity factors
        factors = ComplexityFactors(
            technical_complexity=text_analysis["technical_score"],
            scope_complexity=text_analysis["scope_score"],
            time_pressure=time_pressure,
            environmental_complexity=weather_impact.impact_score if weather_impact else 0,
            dependencies_impact=self._calculate_dependencies_impact(task)
        )

        # 6. Calculate total score
        total_score = self._calculate_total_score(factors, environment_type)

        # Ensure timezone awareness for last_updated
        current_time = datetime.now(timezone.utc)

        return TaskComplexityAnalysis(
            task_id=task_id,
            environment_type=environment_type,
            total_score=total_score,
            factors=factors,
            weather_impact=weather_impact,
            analysis_summary=text_analysis["summary"],
            last_updated=current_time,
            confidence_score=text_analysis["confidence"]
        )

    async def _analyze_task_text(self, name: str, description: str) -> Dict[str, Any]:
        """Analyze task name and description using Ollama's codellama model"""
        prompt = f"""Analyze the following task and provide complexity scores:
        Task Name: {name}
        Description: {description}

        Please analyze the technical complexity, scope, and provide scores on a scale of 0-100.
        Consider:
        1. Technical terms and required expertise
        2. Number of subtasks and requirements
        3. Dependencies and interactions
        4. Clarity of requirements
        5. Potential challenges

        Provide response in JSON format with:
        - technical_score (0-100)
        - scope_score (0-100)
        - summary (brief analysis)
        - confidence (0-1)

        Return only valid JSON, no other text.
        """

        response = requests.post(
            self.ollama_url,
            json={
                "model": "codellama",
                "prompt": prompt,
                "stream": False
            }
        )

        try:
            result = response.json()
            response_text = result["response"]
            analysis = json.loads(response_text)
            return analysis
        except (json.JSONDecodeError, KeyError) as e:
            return {
                "technical_score": 50,
                "scope_score": 50,
                "summary": "Unable to analyze task complexity",
                "confidence": 0.5
            }

    async def _classify_task_environment(self, name: str, description: str) -> TaskEnvironment:
        """Determine if task is indoor, outdoor, or hybrid"""
        # Use the existing weather service's outdoor task detection
        is_outdoor = self.weather_service.is_outdoor_task(description, name)
        
        # If clearly outdoor, return OUTDOOR
        if is_outdoor:
            return TaskEnvironment.OUTDOOR
            
        # For tasks that might have both indoor/outdoor components
        hybrid_keywords = ['installation', 'maintenance', 'setup', 'event', 'inspection']
        text = f"{name} {description}".lower()
        
        if any(keyword in text for keyword in hybrid_keywords):
            return TaskEnvironment.HYBRID
            
        return TaskEnvironment.INDOOR

    async def _get_weather_impact(self, task: Task, location: Optional[str] = None) -> Optional[WeatherImpact]:
        """Get weather impact for outdoor tasks using existing weather service"""
        if not task.deadline:
            return None

        try:
            # Use default location if none found
            city = location or "Harare"
            
            # Get weather analysis from cache service
            weather_data = await self.weather_cache.get_weather_analysis(city)
            
            if not weather_data or 'analysis' not in weather_data:
                return None

            analysis = weather_data['analysis']
            current = analysis['current_conditions']
            trends = analysis['trends']
            recommendations = analysis['recommendations']

            # Calculate impact score based on risk levels and conditions
            impact_score = self._calculate_weather_impact_score(analysis)

            return WeatherImpact(
                temperature=current['temperature'],
                humidity=weather_data['forecast'][0].get('humidity', 0),
                precipitation_probability=weather_data['forecast'][0].get('precipitation', 0),
                wind_speed=weather_data['forecast'][0].get('wind_speed', 0),
                weather_condition=current['weather'],
                impact_score=impact_score,
                analysis=self._generate_weather_analysis(analysis, recommendations)
            )
        except Exception as e:
            print(f"Error getting weather impact: {str(e)}")
            return None

    def _calculate_weather_impact_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate weather impact score based on analysis"""
        score = 50.0  # Base score
        
        # Get risk levels distribution
        risk_levels = analysis['trends']['risk_levels']
        high_risks = sum(1 for r in risk_levels if r == 'high')
        medium_risks = sum(1 for r in risk_levels if r == 'medium')
        
        # Adjust score based on risks
        if high_risks > 0:
            score += (high_risks / len(risk_levels)) * 40
        if medium_risks > 0:
            score += (medium_risks / len(risk_levels)) * 20
            
        # Adjust for outdoor work suitability
        if not analysis['recommendations']['outdoor_work_suitable']:
            score += 10
            
        return min(100.0, score)

    def _generate_weather_analysis(self, analysis: Dict[str, Any], recommendations: Dict[str, Any]) -> str:
        """Generate weather impact analysis"""
        impacts = []
        
        # Add current conditions impact
        current = analysis['current_conditions']
        if current['risk_level'] != 'low':
            impacts.append(f"Current conditions: {current['description']} ({current['risk_level']} risk)")
            
        # Add trend analysis
        if not recommendations['outdoor_work_suitable']:
            impacts.append("Weather conditions not suitable for outdoor work")
            
        if recommendations['risk_hours']:
            risk_hours = [f"{h}:00" for h in recommendations['risk_hours']]
            impacts.append(f"High risk hours: {', '.join(risk_hours)}")
            
        if not impacts:
            return "Weather conditions are favorable for outdoor work"
        
        return "Weather challenges: " + "; ".join(impacts)

    def _calculate_time_pressure(self, task: Task) -> float:
        """Calculate time pressure score based on deadline and planned hours"""
        if not task.deadline:
            return 50.0  # Default moderate pressure if no deadline

        now = datetime.now(timezone.utc)
        
        # Ensure deadline is timezone-aware
        deadline = task.deadline.replace(tzinfo=timezone.utc) if task.deadline.tzinfo is None else task.deadline
        
        days_until_deadline = (deadline - now).days
        planned_hours = task.planned_hours or 8  # Default to 8 hours if not specified

        # Calculate base pressure score
        if days_until_deadline <= 0:
            return 100.0
        elif days_until_deadline <= 1:
            return 90.0
        elif days_until_deadline <= 3:
            return 80.0
        elif days_until_deadline <= 7:
            return 70.0
        else:
            return max(30.0, 70.0 - (days_until_deadline - 7) * 2)

    def _calculate_dependencies_impact(self, task: Task) -> float:
        """Calculate impact of task dependencies"""
        dependency_count = len(task.depends_on) if hasattr(task, 'depends_on') else 0
        
        if dependency_count == 0:
            return 0.0
        elif dependency_count <= 2:
            return 30.0
        elif dependency_count <= 5:
            return 60.0
        else:
            return min(100.0, 60.0 + (dependency_count - 5) * 10)

    def _calculate_total_score(self, factors: ComplexityFactors, environment_type: TaskEnvironment) -> float:
        """Calculate final complexity score"""
        weights = {
            "technical": 0.3,
            "scope": 0.2,
            "time": 0.25,
            "environment": 0.15,
            "dependencies": 0.1
        }

        # Adjust weights based on environment
        if environment_type == TaskEnvironment.OUTDOOR:
            weights["environment"] = 0.25
            weights["technical"] = 0.25
            weights["scope"] = 0.15
        elif environment_type == TaskEnvironment.HYBRID:
            weights["environment"] = 0.20
            weights["technical"] = 0.25
            weights["scope"] = 0.20

        total_score = (
            factors.technical_complexity * weights["technical"] +
            factors.scope_complexity * weights["scope"] +
            factors.time_pressure * weights["time"] +
            factors.environmental_complexity * weights["environment"] +
            factors.dependencies_impact * weights["dependencies"]
        )

        return round(total_score, 2) 