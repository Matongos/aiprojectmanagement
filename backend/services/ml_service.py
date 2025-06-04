from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta, timezone
import numpy as np
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, accuracy_score
import joblib
import json
import pandas as pd

from models.task import Task, TaskType
from models.project import Project, ProjectMember
from models.time_entry import TimeEntry
from models.user import User
from models.ml_models import (
    TaskPrediction, TeamPerformanceMetrics, 
    SuccessPattern, MLModel, HistoricalPattern
)

class MLService:
    def __init__(self, db: Session):
        self.db = db
        self.scaler = StandardScaler()
        
    def _prepare_task_features(self, task: Task) -> Dict[str, Any]:
        """Extract and prepare features for task prediction"""
        features = {
            'planned_hours': task.planned_hours or 0,
            'priority_level': self._encode_priority(task.priority),
            'complexity_score': self._calculate_complexity_score(task),
            'dependency_count': len(task.depends_on) if task.depends_on else 0,
            'team_experience': self._get_team_experience_score(task),
            'similar_tasks_avg_time': self._get_similar_tasks_completion_time(task),
            'project_health_score': self._get_project_health_score(task.project) if task.project else 0,
        }
        return features
        
    def _encode_priority(self, priority: str) -> float:
        """Convert priority string to numeric value"""
        priority_map = {
            'low': 0.0,
            'normal': 0.5,
            'high': 0.75,
            'urgent': 1.0
        }
        return priority_map.get(priority.lower(), 0.5)
        
    def _calculate_complexity_score(self, task: Task) -> float:
        """Calculate task complexity score based on various factors"""
        score = 0.0
        
        # Base complexity from description length and key terms
        if task.description:
            complexity_terms = ['complex', 'difficult', 'challenging', 'critical']
            score += min(len(task.description.split()) / 100.0, 0.5)  # Length factor
            score += sum(0.1 for term in complexity_terms if term in task.description.lower())
            
        # Dependency complexity
        if task.depends_on:
            score += min(len(task.depends_on) * 0.1, 0.3)
            
        # Time estimation factor
        if task.planned_hours:
            score += min(task.planned_hours / 40.0, 0.2)  # Cap at 40 hours
            
        return min(score, 1.0)  # Normalize to 0-1
        
    def _get_team_experience_score(self, task: Task) -> float:
        """Calculate team experience score for task"""
        if not task.assignee:
            return 0.0
            
        # Get user's completed tasks in last 90 days
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
        completed_tasks = self.db.query(Task).filter(
            Task.assigned_to == task.assignee.id,
            Task.state == 'done',
            Task.end_date >= ninety_days_ago
        ).count()
        
        # Get user's role experience
        if task.project:
            project_member = self.db.query(ProjectMember).filter(
                ProjectMember.project_id == task.project.id,
                ProjectMember.user_id == task.assignee.id
            ).first()
            
            if project_member and project_member.role:
                # Convert ProjectRole enum to string using to_string method
                role_str = project_member.role.to_string()
                role_multiplier = {
                    'manager': 1.3,
                    'member': 1.0,
                    'viewer': 0.8
                }.get(role_str, 1.0)
                
                return min((completed_tasks * 0.1) * role_multiplier, 1.0)
        
        return min(completed_tasks * 0.1, 1.0)
        
    def _get_similar_tasks_completion_time(self, task: Task) -> float:
        """Get average completion time of similar tasks"""
        if not task.project:
            return 0.0
            
        # Find similar tasks by matching keywords in title/description
        keywords = set((task.name + " " + (task.description or "")).lower().split())
        
        similar_tasks = self.db.query(Task).filter(
            Task.project_id == task.project.id,
            Task.state == 'done',
            Task.id != task.id
        ).all()
        
        completion_times = []
        for similar_task in similar_tasks:
            similar_keywords = set((similar_task.name + " " + (similar_task.description or "")).lower().split())
            similarity = len(keywords & similar_keywords) / len(keywords | similar_keywords)
            
            if similarity > 0.3 and similar_task.start_date and similar_task.end_date:
                # Ensure both dates are timezone-aware
                start_date = similar_task.start_date.replace(tzinfo=timezone.utc) if similar_task.start_date.tzinfo is None else similar_task.start_date
                end_date = similar_task.end_date.replace(tzinfo=timezone.utc) if similar_task.end_date.tzinfo is None else similar_task.end_date
                hours = (end_date - start_date).total_seconds() / 3600
                completion_times.append(hours)
                
        return sum(completion_times) / len(completion_times) if completion_times else 0.0
        
    def _get_project_health_score(self, project: Project) -> float:
        """Calculate project health score"""
        if not project:
            return 0.5
            
        # Calculate completion rate
        total_tasks = len(project.tasks)
        if total_tasks == 0:
            return 0.5
            
        completed_tasks = len([t for t in project.tasks if t.state == 'done'])
        completion_rate = completed_tasks / total_tasks
        
        # Calculate deadline adherence
        now = datetime.now(timezone.utc)
        overdue_tasks = len([t for t in project.tasks 
                           if t.deadline and 
                           (t.deadline.replace(tzinfo=timezone.utc) if t.deadline.tzinfo is None else t.deadline) < now 
                           and t.state != 'done'])
        deadline_score = 1.0 - (overdue_tasks / total_tasks if total_tasks > 0 else 0)
        
        # Team velocity
        thirty_days_ago = now - timedelta(days=30)
        recent_completed = len([t for t in project.tasks 
                              if t.state == 'done' and t.end_date 
                              and (t.end_date.replace(tzinfo=timezone.utc) if t.end_date.tzinfo is None else t.end_date) >= thirty_days_ago])
        velocity_score = min(recent_completed / 10.0, 1.0)  # Normalize to 0-1
        
        # Combine scores with weights
        return (completion_rate * 0.4 + deadline_score * 0.4 + velocity_score * 0.2)
        
    async def predict_task_completion_time(self, task_id: int) -> Dict[str, Any]:
        """Predict task completion time using ML model"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
            
        # Get or create ML model
        model = self._get_or_train_completion_time_model()
        
        # Prepare features
        features = self._prepare_task_features(task)
        feature_vector = np.array([list(features.values())])
        
        # Make prediction
        if hasattr(self, 'scaler') and self.scaler:
            feature_vector = self.scaler.transform(feature_vector)
        
        predicted_hours = float(model.predict(feature_vector)[0])
        confidence_score = self._calculate_prediction_confidence(model, feature_vector)
        
        # Store prediction
        prediction = TaskPrediction(
            task_id=task.id,
            predicted_completion_time=predicted_hours,
            confidence_score=confidence_score,
            features_used=features
        )
        self.db.add(prediction)
        self.db.commit()
        
        return {
            "task_id": task.id,
            "predicted_hours": round(predicted_hours, 2),
            "confidence_score": round(confidence_score, 2),
            "features_used": features
        }
        
    def _get_or_train_completion_time_model(self) -> RandomForestRegressor:
        """Get existing ML model or train a new one"""
        model_record = self.db.query(MLModel).filter(
            MLModel.model_type == 'completion_time_predictor',
            MLModel.is_active == True
        ).order_by(MLModel.created_at.desc()).first()
        
        if model_record and model_record.last_trained:
            # Check if model is recent (trained within last 7 days)
            if model_record.last_trained >= datetime.now(timezone.utc) - timedelta(days=7):
                return joblib.load(f'models/completion_time_{model_record.model_version}.joblib')
        
        # Train new model
        return self._train_completion_time_model()
        
    def _train_completion_time_model(self) -> RandomForestRegressor:
        """Train a new completion time prediction model"""
        # Get completed tasks with actual completion times
        completed_tasks = self.db.query(Task).filter(
            Task.state == 'done',
            Task.start_date.isnot(None),
            Task.end_date.isnot(None)
        ).all()
        
        if not completed_tasks:
            raise ValueError("No completed tasks available for training")
            
        # Prepare training data
        X = []  # Features
        y = []  # Target (actual completion times)
        
        for task in completed_tasks:
            features = self._prepare_task_features(task)
            # Ensure both dates are timezone-aware
            start_date = task.start_date.replace(tzinfo=timezone.utc) if task.start_date.tzinfo is None else task.start_date
            end_date = task.end_date.replace(tzinfo=timezone.utc) if task.end_date.tzinfo is None else task.end_date
            actual_hours = (end_date - start_date).total_seconds() / 3600
            
            X.append(list(features.values()))
            y.append(actual_hours)
            
        X = np.array(X)
        y = np.array(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test_scaled)
        mse = mean_squared_error(y_test, y_pred)
        
        # Save model
        version = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')
        model_path = f'models/completion_time_{version}.joblib'
        joblib.dump(model, model_path)
        
        # Store model metadata
        model_record = MLModel(
            model_name=f"completion_time_{version}",
            model_type="completion_time_predictor",
            model_version=version,
            performance_metrics={
                "mse": mse,
                "rmse": np.sqrt(mse),
                "test_size": len(y_test)
            },
            hyperparameters={
                "n_estimators": 100,
                "random_state": 42
            },
            feature_importance=dict(zip(
                ["planned_hours", "priority", "complexity", "dependencies", 
                 "team_experience", "similar_tasks", "project_health"],
                model.feature_importances_.tolist()
            )),
            last_trained=datetime.now(timezone.utc),
            is_active=True
        )
        self.db.add(model_record)
        self.db.commit()
        
        return model
        
    def _calculate_prediction_confidence(
        self, 
        model: RandomForestRegressor, 
        feature_vector: np.ndarray
    ) -> float:
        """Calculate confidence score for prediction"""
        # Get individual predictions from all trees
        predictions = [tree.predict(feature_vector)[0] 
                      for tree in model.estimators_]
        
        # Calculate confidence based on prediction variance
        std_dev = np.std(predictions)
        mean_pred = np.mean(predictions)
        cv = std_dev / mean_pred  # Coefficient of variation
        
        # Convert to confidence score (0-1)
        confidence = 1.0 / (1.0 + cv)
        return min(max(confidence, 0.0), 1.0)
        
    async def analyze_team_performance(self, project_id: int) -> Dict[str, Any]:
        """Analyze team performance using ML insights"""
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError(f"Project {project_id} not found")
            
        # Calculate current period metrics
        current_period = datetime.now(timezone.utc).strftime('%Y-%m')
        
        # Get team velocity
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        completed_tasks = len([t for t in project.tasks 
                             if t.state == 'done' 
                             and t.end_date 
                             and t.end_date >= thirty_days_ago])
        velocity = completed_tasks / 30.0  # Tasks per day
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(project)
        
        # Calculate collaboration score
        collaboration_score = self._calculate_collaboration_score(project)
        
        # Calculate efficiency score
        efficiency_score = self._calculate_efficiency_score(project)
        
        # Store metrics
        metrics = TeamPerformanceMetrics(
            project_id=project.id,
            time_period=current_period,
            velocity=velocity,
            quality_score=quality_score,
            collaboration_score=collaboration_score,
            efficiency_score=efficiency_score,
            metrics_data={
                "completed_tasks": completed_tasks,
                "active_tasks": len([t for t in project.tasks if t.state == 'in_progress']),
                "team_size": len(project.project_members),
                "detailed_scores": {
                    "quality": quality_score,
                    "collaboration": collaboration_score,
                    "efficiency": efficiency_score
                }
            }
        )
        self.db.add(metrics)
        self.db.commit()
        
        return {
            "project_id": project.id,
            "time_period": current_period,
            "metrics": {
                "velocity": round(velocity, 2),
                "quality_score": round(quality_score, 2),
                "collaboration_score": round(collaboration_score, 2),
                "efficiency_score": round(efficiency_score, 2)
            },
            "insights": self._generate_performance_insights(metrics)
        }
        
    def _calculate_quality_score(self, project: Project) -> float:
        """Calculate quality score based on rework and bugs"""
        total_tasks = len(project.tasks)
        if total_tasks == 0:
            return 0.0
            
        # Count tasks that needed rework
        rework_tasks = len([t for t in project.tasks 
                          if any(c.content and 'rework' in c.content.lower() 
                                for c in t.comments)])
        
        # Count bug reports
        bug_tasks = len([t for t in project.tasks 
                        if t.task_type == TaskType.BUG_FIX.value or 
                        (t.description and 'bug' in t.description.lower())])
        
        # Calculate quality score (inverse of issues)
        quality_score = 1.0 - ((rework_tasks + bug_tasks) / total_tasks)
        return max(min(quality_score, 1.0), 0.0)
        
    def _calculate_collaboration_score(self, project: Project) -> float:
        """Calculate collaboration score based on interactions"""
        if not project.project_members:
            return 0.0
            
        # Calculate interaction score based on comments and activities
        total_interactions = sum(len(task.comments) + len(task.activities) 
                               for task in project.tasks)
        avg_interactions = total_interactions / len(project.project_members)
        
        # Calculate dependency management score
        dependency_score = self._calculate_dependency_score(project)
        
        # Combine scores
        return min((avg_interactions * 0.1 + dependency_score) / 2.0, 1.0)
        
    def _calculate_dependency_score(self, project: Project) -> float:
        """Calculate how well dependencies are managed"""
        tasks_with_deps = [t for t in project.tasks if t.depends_on]
        if not tasks_with_deps:
            return 1.0
            
        # Calculate percentage of dependencies completed on time
        on_time_deps = 0
        total_deps = 0
        
        for task in tasks_with_deps:
            for dep in task.depends_on:
                total_deps += 1
                if dep.state == 'done' and dep.end_date and task.start_date:
                    if dep.end_date <= task.start_date:
                        on_time_deps += 1
                        
        return on_time_deps / total_deps if total_deps > 0 else 1.0
        
    def _calculate_efficiency_score(self, project: Project) -> float:
        """Calculate efficiency score based on time estimates vs actuals"""
        tasks_with_estimates = [t for t in project.tasks 
                              if t.planned_hours and t.state == 'done']
        if not tasks_with_estimates:
            return 0.0
            
        efficiency_scores = []
        for task in tasks_with_estimates:
            if task.start_date and task.end_date:
                actual_hours = (task.end_date - task.start_date).total_seconds() / 3600
                estimate_ratio = min(task.planned_hours / actual_hours 
                                   if actual_hours > 0 else 1.0, 2.0)
                efficiency_scores.append(estimate_ratio)
                
        return sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0.0
        
    def _generate_performance_insights(self, metrics: TeamPerformanceMetrics) -> List[str]:
        """Generate insights from performance metrics"""
        insights = []
        
        # Velocity insights
        if metrics.velocity < 0.5:
            insights.append("Team velocity is below average - consider reducing work in progress")
        elif metrics.velocity > 1.5:
            insights.append("High team velocity - ensure quality is maintained")
            
        # Quality insights
        if metrics.quality_score < 0.7:
            insights.append("Quality metrics indicate need for more thorough testing")
        elif metrics.quality_score > 0.9:
            insights.append("Excellent quality maintenance - document successful practices")
            
        # Collaboration insights
        if metrics.collaboration_score < 0.6:
            insights.append("Team collaboration could be improved - consider team building activities")
        elif metrics.collaboration_score > 0.8:
            insights.append("Strong team collaboration observed")
            
        # Efficiency insights
        if metrics.efficiency_score < 0.7:
            insights.append("Time estimation accuracy needs improvement")
        elif metrics.efficiency_score > 0.9:
            insights.append("Excellent time estimation accuracy")
            
        return insights

# Create a singleton instance
_ml_service = None

def get_ml_service(db: Session) -> MLService:
    """Get or create singleton ML service instance"""
    global _ml_service
    if _ml_service is None:
        _ml_service = MLService(db)
    return _ml_service 