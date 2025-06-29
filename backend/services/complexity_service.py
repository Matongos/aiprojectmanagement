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
import logging

logger = logging.getLogger(__name__)

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
        """Analyze task name and description using AI for universal complexity assessment"""
        prompt = f"""Analyze the following task and provide complexity scores for ANY industry or field:

        Task Name: {name}
        Description: {description}

Please analyze the complexity across ALL industries and provide scores on a scale of 0-100.

UNIVERSAL COMPLEXITY FACTORS TO CONSIDER:
1. Technical Complexity (0-100):
   - Required technical skills, tools, or equipment
   - Specialized knowledge or certifications needed
   - Complexity of procedures or processes
   - Examples: Software development, medical procedures, construction techniques, financial analysis

2. Scope Complexity (0-100):
   - Number of subtasks and requirements
   - Dependencies and interactions
   - Clarity of requirements
   - Potential challenges and risks
   - Examples: Large marketing campaigns, construction projects, research studies, event planning

3. Industry-Specific Considerations:
   - Healthcare: Patient safety, regulatory compliance, medical procedures
   - Construction: Safety regulations, building codes, physical labor
   - Marketing: Creative requirements, target audience, campaign coordination
   - Education: Curriculum development, student engagement, assessment methods
   - Manufacturing: Quality control, production processes, safety protocols
   - Retail: Customer service, inventory management, sales processes
   - Finance: Regulatory compliance, accuracy requirements, risk assessment

        Provide response in JSON format with:
        - technical_score (0-100)
        - scope_score (0-100)
- summary (brief analysis of complexity factors)
        - confidence (0-1)

        Return only valid JSON, no other text.
        """

        response = requests.post(
            self.ollama_url,
            json={
                "model": "mistral",  # Changed from codellama to mistral for better universal analysis
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
                "summary": "Unable to analyze task complexity - using default scores",
                "confidence": 0.5
            }

    async def _classify_task_environment(self, name: str, description: str) -> TaskEnvironment:
        """AI-powered classification to determine if task is indoor, outdoor, or hybrid"""
        try:
            prompt = f"""Analyze the following task and determine its work environment:

TASK:
Name: {name}
Description: {description}

ENVIRONMENT CLASSIFICATION:
Classify the task into one of these categories:

1. INDOOR: Tasks performed primarily inside buildings, offices, or controlled environments
   - Software development, coding, design work
   - Office work, administration, management
   - Content creation, writing, marketing
   - Financial work, accounting, analysis
   - Indoor manufacturing, assembly
   - Indoor healthcare, education, research

2. OUTDOOR: Tasks performed primarily outside or in uncontrolled environments
   - Construction, building, landscaping
   - Agriculture, farming, gardening
   - Outdoor maintenance, repair, installation
   - Transportation, delivery, field work
   - Outdoor events, concerts, festivals
   - Outdoor healthcare (home visits, emergency response)

3. HYBRID: Tasks that involve both indoor and outdoor work
   - Installation work that requires both setup and outdoor access
   - Maintenance that involves both office work and field work
   - Events that have both indoor and outdoor components
   - Service calls that require travel and on-site work

You MUST return ONLY valid JSON in this exact format:
{{
    "environment": "indoor",
    "reasoning": "Brief explanation of why this classification was chosen",
    "confidence": 0.95
}}

Return only valid JSON, no other text."""

            response = requests.post(
                self.ollama_url,
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                response_text = result["response"]
                analysis = json.loads(response_text)
                
                environment = analysis.get("environment", "indoor").lower()
                reasoning = analysis.get("reasoning", "AI analysis provided")
                confidence = analysis.get("confidence", 0.8)
                
                logger.info(f"AI environment classification for '{name}': {environment} (confidence: {confidence}) - {reasoning}")
                
                # Map AI response to TaskEnvironment enum
                if environment == "outdoor":
                    return TaskEnvironment.OUTDOOR
                elif environment == "hybrid":
                    return TaskEnvironment.HYBRID
                else:
                    return TaskEnvironment.INDOOR
                    
            else:
                logger.warning(f"AI environment classification failed, falling back to rule-based: {response.status_code}")
                return self._fallback_environment_classification(name, description)
                
        except Exception as e:
            logger.error(f"Error in AI environment classification: {str(e)}")
            return self._fallback_environment_classification(name, description)

    def _fallback_environment_classification(self, name: str, description: str) -> TaskEnvironment:
        """Fallback rule-based classification when AI fails"""
        text = f"{name} {description}".lower()
        
        # INDOOR TASKS (clear indoor indicators)
        indoor_keywords = [
            # Software & IT
            'develop', 'code', 'programming', 'software', 'website', 'app', 'application',
            'html', 'css', 'javascript', 'database', 'api', 'backend', 'frontend',
            'design', 'ui', 'ux', 'wireframe', 'mockup', 'prototype',
            'testing', 'debug', 'deploy', 'hosting', 'server', 'cloud',
            
            # Office & Administrative
            'admin', 'management', 'coordination', 'planning', 'organization',
            'reporting', 'documentation', 'meeting', 'presentation', 'analysis',
            'research', 'data', 'report', 'study', 'survey', 'investigation',
            
            # Creative & Content
            'content', 'writing', 'copy', 'text', 'creative', 'art', 'graphic',
            'marketing', 'advertising', 'social media', 'seo', 'campaign',
            
            # Financial & Business
            'financial', 'accounting', 'budget', 'expense', 'invoice', 'tax',
            'audit', 'reporting', 'sales', 'customer', 'client', 'business',
            
            # Healthcare (indoor)
            'patient care', 'medical', 'treatment', 'diagnosis', 'consultation',
            'laboratory', 'testing', 'examination', 'therapy', 'counseling',
            
            # Education (indoor)
            'teaching', 'education', 'training', 'curriculum', 'lesson',
            'student', 'learning', 'classroom', 'lecture', 'workshop',
            
            # Manufacturing (indoor)
            'manufacturing', 'production', 'assembly', 'quality control',
            'factory', 'warehouse', 'inventory', 'processing'
        ]
        
        # OUTDOOR TASKS (clear outdoor indicators)
        outdoor_keywords = [
            # Construction & Manual (physical outdoor work)
            'construction', 'building', 'roofing', 'landscaping', 'gardening', 'excavation',
            'outdoor', 'field', 'site', 'ground', 'yard', 'park', 'street', 'road',
            'paint exterior', 'repair exterior', 'build exterior', 'inspect exterior',
            
            # Agriculture & Farming
            'farming', 'agriculture', 'harvest', 'planting', 'irrigation', 'livestock',
            'crop', 'soil', 'fertilizer', 'pesticide',
            
            # Transportation & Delivery (physical)
            'delivery', 'transportation', 'driving', 'shipping', 'logistics',
            'truck', 'vehicle', 'route', 'dispatch',
            
            # Events & Entertainment (outdoor)
            'outdoor event', 'concert', 'festival', 'venue setup', 'outdoor venue',
            'stadium', 'amphitheater', 'park event',
            
            # Maintenance & Services (outdoor)
            'outdoor maintenance', 'outdoor repair', 'outdoor installation', 
            'outdoor inspection', 'outdoor survey', 'outdoor cleaning',
            
            # Healthcare (outdoor)
            'home visit', 'mobile clinic', 'field hospital', 'emergency response',
            'ambulance', 'paramedic', 'outdoor medical',
            
            # Sales & Marketing (outdoor)
            'door-to-door', 'street marketing', 'outdoor advertising', 'trade show',
            'outdoor sales', 'outdoor promotion',
            
            # Education (outdoor)
            'field trip', 'outdoor education', 'sports', 'recreation',
            'outdoor activity', 'outdoor training'
        ]
        
        # HYBRID TASKS (mix of indoor/outdoor)
        hybrid_keywords = [
            'installation', 'maintenance', 'repair', 'setup', 'event', 'inspection', 'survey',
            'delivery', 'service call', 'home visit', 'site visit', 'field work',
            'mobile', 'on-site', 'client visit', 'meeting', 'presentation'
        ]
        
        # Check for indoor tasks first (most specific)
        if any(keyword in text for keyword in indoor_keywords):
            return TaskEnvironment.INDOOR
            
        # Check for outdoor tasks
        if any(keyword in text for keyword in outdoor_keywords):
            return TaskEnvironment.OUTDOOR
            
        # Check for hybrid tasks
        if any(keyword in text for keyword in hybrid_keywords):
            return TaskEnvironment.HYBRID
            
        # Default to indoor (office, factory, hospital, school, etc.)
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