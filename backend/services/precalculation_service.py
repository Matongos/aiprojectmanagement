from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.task import Task
from models.project import Project
from models.metrics import TaskMetrics
from fastapi import HTTPException
import redis
import json
from typing import Dict, Any, Optional, List
import asyncio
import os
from models.user import User

class PreCalculationService:
    def __init__(self):
        # Initialize Redis connection with fallback options
        self.redis = self._initialize_redis()
        self.calculation_lock = asyncio.Lock()
        
    def _initialize_redis(self) -> redis.Redis:
        """Initialize Redis connection with fallback options"""
        redis_configs = [
            # Default local connection
            {"host": "localhost", "port": 6379},
            # Windows Service default
            {"host": "127.0.0.1", "port": 6379},
            # Memurai default
            {"host": "127.0.0.1", "port": 6379, "password": None},
            # WSL default
            {"host": "localhost", "port": 6379, "password": None}
        ]
        
        # Try each configuration until one works
        for config in redis_configs:
            try:
                client = redis.Redis(
                    **config,
                    db=0,
                    decode_responses=True,
                    socket_timeout=1,
                    socket_connect_timeout=1
                )
                # Test the connection
                client.ping()
                print(f"Successfully connected to Redis at {config['host']}:{config['port']}")
                return client
            except redis.ConnectionError as e:
                print(f"Failed to connect to Redis with config {config}: {str(e)}")
                continue
            except Exception as e:
                print(f"Unexpected error connecting to Redis with config {config}: {str(e)}")
                continue
        
        # If all connections fail, use a dummy cache
        print("WARNING: Could not connect to Redis. Using in-memory fallback cache.")
        return self._create_fallback_cache()
    
    def _create_fallback_cache(self) -> Any:
        """Create a simple in-memory cache as fallback"""
        class FallbackCache:
            def __init__(self):
                self._cache = {}
            
            def get(self, key):
                # Remove expired items
                now = datetime.utcnow().timestamp()
                self._cache = {k: v for k, v in self._cache.items() 
                             if v['expires'] > now}
                
                if key in self._cache:
                    return self._cache[key]['value']
                return None
            
            def setex(self, key, expires_in, value):
                expires_at = datetime.utcnow().timestamp() + expires_in.total_seconds()
                self._cache[key] = {
                    'value': value,
                    'expires': expires_at
                }
            
            def ping(self):
                return True
        
        return FallbackCache()

    async def calculate_project_metrics(self, db: Session, project_id: int) -> Dict[str, Any]:
        """Calculate and cache project metrics"""
        cache_key = f"project_metrics:{project_id}"
        
        try:
            # Try to get cached data first
            cached_data = self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            
            async with self.calculation_lock:
                # Calculate metrics
                metrics = {
                    "total_tasks": db.query(Task).filter(Task.project_id == project_id).count(),
                    "completed_tasks": db.query(Task).filter(
                        Task.project_id == project_id,
                        Task.state == "done"
                    ).count(),
                    "in_progress_tasks": db.query(Task).filter(
                        Task.project_id == project_id,
                        Task.state == "in_progress"
                    ).count(),
                    "blocked_tasks": db.query(Task).filter(
                        Task.project_id == project_id,
                        Task.state == "blocked"
                    ).count(),
                    "total_time_spent": db.query(func.sum(TaskMetrics.actual_duration)).\
                        join(Task).\
                        filter(Task.project_id == project_id).\
                        scalar() or 0,
                    "average_completion_time": db.query(func.avg(TaskMetrics.actual_duration)).\
                        join(Task).\
                        filter(Task.project_id == project_id).\
                        scalar() or 0,
                    "efficiency_score": self._calculate_efficiency_score(db, project_id),
                    "risk_factors": self._identify_risk_factors(db, project_id),
                    "resource_utilization": self._calculate_resource_utilization(db, project_id),
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                # Cache the results with 1-minute expiration
                self.redis.setex(
                    cache_key,
                    timedelta(minutes=1),
                    json.dumps(metrics)
                )
                
                return metrics
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to calculate project metrics: {str(e)}"
            )
    
    async def calculate_task_metrics(self, db: Session, task_id: int) -> Dict[str, Any]:
        """Calculate and cache task-specific metrics"""
        cache_key = f"task_metrics:{task_id}"
        
        try:
            # Try to get cached data first
            cached_data = self.redis.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
            
            async with self.calculation_lock:
                task = db.query(Task).filter(Task.id == task_id).first()
                if not task:
                    raise HTTPException(status_code=404, detail="Task not found")
                
                # Calculate delay metrics
                delay_metrics = self._calculate_delay_metrics(task)
                
                # Calculate resource metrics
                resource_metrics = self._calculate_resource_metrics(db, task)
                
                # Calculate completion metrics
                completion_metrics = self._calculate_completion_metrics(task)
                
                # Calculate risk metrics
                risk_metrics = self._calculate_risk_metrics(db, task)
                
                metrics = {
                    "time_spent": task.metrics.actual_duration if task.metrics else 0,
                    "estimated_remaining_time": self._calculate_remaining_time(task),
                    "completion_percentage": task.progress,
                    "dependency_status": self._check_dependencies(db, task),
                    "risk_level": self._calculate_risk_level(task),
                    "performance_indicators": self._calculate_performance_indicators(task),
                    "resource_conflicts": self._identify_resource_conflicts(db, task),
                    "delay_analysis": delay_metrics,
                    "resource_analysis": resource_metrics,
                    "completion_analysis": completion_metrics,
                    "risk_analysis": risk_metrics,
                    "last_updated": datetime.utcnow().isoformat()
                }
                
                # Cache the results with 30-second expiration for tasks
                self.redis.setex(
                    cache_key,
                    timedelta(seconds=30),
                    json.dumps(metrics)
                )
                
                return metrics
                
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to calculate task metrics: {str(e)}"
            )
    
    def _calculate_efficiency_score(self, db: Session, project_id: int) -> float:
        """Calculate project efficiency score"""
        try:
            tasks = db.query(Task).filter(Task.project_id == project_id).all()
            if not tasks:
                return 0.0
                
            total_score = 0
            for task in tasks:
                if task.metrics:
                    # Consider factors like time estimate accuracy, rework time, etc.
                    accuracy = task.metrics.time_estimate_accuracy or 1
                    rework_ratio = task.metrics.rework_hours / task.metrics.actual_duration if task.metrics.actual_duration > 0 else 1
                    total_score += (accuracy * (1 - rework_ratio))
                    
            return total_score / len(tasks)
        except:
            return 0.0
    
    def _identify_risk_factors(self, db: Session, project_id: int) -> list:
        """Identify project risk factors"""
        risks = []
        try:
            tasks = db.query(Task).filter(Task.project_id == project_id).all()
            
            # Check for overdue tasks
            overdue = [t for t in tasks if t.deadline and t.deadline < datetime.utcnow() and t.state != "done"]
            if overdue:
                risks.append({"type": "overdue_tasks", "count": len(overdue)})
                
            # Check for blocked tasks
            blocked = [t for t in tasks if t.state == "blocked"]
            if blocked:
                risks.append({"type": "blocked_tasks", "count": len(blocked)})
                
            # Check for resource conflicts
            resource_conflicts = self._check_resource_conflicts(tasks)
            if resource_conflicts:
                risks.append({"type": "resource_conflicts", "details": resource_conflicts})
                
            return risks
        except:
            return []
    
    def _calculate_resource_utilization(self, db: Session, project_id: int) -> Dict[str, float]:
        """Calculate resource utilization for the project"""
        try:
            # Get all tasks and their assignments
            tasks = db.query(Task).filter(Task.project_id == project_id).all()
            
            utilization = {}
            for task in tasks:
                if task.assigned_to:
                    if task.assigned_to not in utilization:
                        utilization[task.assigned_to] = {
                            "total_hours": 0,
                            "available_hours": 40  # Assuming 40-hour work week
                        }
                    
                    if task.metrics and task.state == "in_progress":
                        utilization[task.assigned_to]["total_hours"] += task.metrics.actual_duration
                        
            # Calculate utilization percentages
            return {
                str(user_id): (data["total_hours"] / data["available_hours"]) * 100
                for user_id, data in utilization.items()
            }
        except:
            return {}
    
    def _calculate_remaining_time(self, task: Task) -> float:
        """Calculate estimated remaining time for a task"""
        try:
            if task.metrics and task.metrics.actual_duration > 0:
                if task.progress >= 100:
                    return 0
                return (task.planned_hours * (100 - task.progress) / 100)
            return task.planned_hours
        except:
            return 0
    
    def _check_dependencies(self, db: Session, task: Task) -> Dict[str, Any]:
        """Check task dependencies status"""
        try:
            blocked_by = []
            for dep in task.depends_on:
                if dep.state != "done":
                    blocked_by.append({
                        "task_id": dep.id,
                        "name": dep.name,
                        "state": dep.state
                    })
            
            return {
                "is_blocked": len(blocked_by) > 0,
                "blocked_by": blocked_by
            }
        except:
            return {"is_blocked": False, "blocked_by": []}
    
    def _calculate_risk_level(self, task: Task) -> str:
        """Calculate risk level for a task"""
        try:
            risk_score = 0
            
            # Check deadline
            if task.deadline and task.deadline < datetime.utcnow() and task.state != "done":
                risk_score += 3
                
            # Check progress vs time spent
            if task.metrics and task.metrics.actual_duration > task.planned_hours:
                risk_score += 2
                
            # Check dependencies
            if any(dep.state != "done" for dep in task.depends_on):
                risk_score += 1
                
            if risk_score >= 4:
                return "high"
            elif risk_score >= 2:
                return "medium"
            return "low"
        except:
            return "unknown"
    
    def _calculate_performance_indicators(self, task: Task) -> Dict[str, Any]:
        """Calculate performance indicators for a task"""
        try:
            if not task.metrics:
                return {}
                
            return {
                "time_efficiency": task.metrics.time_estimate_accuracy if task.metrics.time_estimate_accuracy else 1,
                "quality_score": 1 - (task.metrics.rework_hours / task.metrics.actual_duration if task.metrics.actual_duration > 0 else 0),
                "complexity_level": task.metrics.complexity_score
            }
        except:
            return {}
    
    def _identify_resource_conflicts(self, db: Session, task: Task) -> list:
        """Identify resource conflicts for a task"""
        try:
            if not task.assigned_to:
                return []
                
            conflicts = []
            overlapping_tasks = db.query(Task).filter(
                Task.assigned_to == task.assigned_to,
                Task.id != task.id,
                Task.state == "in_progress"
            ).all()
            
            for other_task in overlapping_tasks:
                if (task.start_date and other_task.start_date and 
                    task.end_date and other_task.end_date):
                    if (task.start_date <= other_task.end_date and 
                        task.end_date >= other_task.start_date):
                        conflicts.append({
                            "task_id": other_task.id,
                            "name": other_task.name,
                            "overlap_period": [
                                max(task.start_date, other_task.start_date).isoformat(),
                                min(task.end_date, other_task.end_date).isoformat()
                            ]
                        })
            
            return conflicts
        except:
            return []
    
    def _check_resource_conflicts(self, tasks: list) -> list:
        """Check for resource conflicts across tasks"""
        try:
            conflicts = []
            resource_assignments = {}
            
            for task in tasks:
                if task.assigned_to and task.state == "in_progress":
                    if task.assigned_to not in resource_assignments:
                        resource_assignments[task.assigned_to] = []
                    resource_assignments[task.assigned_to].append(task)
            
            for user_id, user_tasks in resource_assignments.items():
                if len(user_tasks) > 1:
                    conflicts.append({
                        "user_id": user_id,
                        "task_count": len(user_tasks),
                        "tasks": [{"id": t.id, "name": t.name} for t in user_tasks]
                    })
            
            return conflicts
        except:
            return []

    def _calculate_delay_metrics(self, task: Task) -> Dict[str, Any]:
        """Calculate detailed delay metrics"""
        try:
            now = datetime.utcnow()
            metrics = {
                "is_delayed": False,
                "delay_duration": 0,
                "delay_percentage": 0,
                "delay_impact": "none",
                "recovery_possible": True,
                "suggested_actions": []
            }
            
            if task.deadline and task.start_date:
                total_allocated_time = (task.deadline - task.start_date).total_seconds()
                time_elapsed = (now - task.start_date).total_seconds()
                expected_progress = (time_elapsed / total_allocated_time) * 100 if total_allocated_time > 0 else 0
                
                if task.progress < expected_progress:
                    metrics["is_delayed"] = True
                    metrics["delay_percentage"] = expected_progress - task.progress
                    
                    # Calculate delay duration in hours
                    expected_completion_at_current_rate = task.start_date + timedelta(
                        seconds=total_allocated_time * (100 / task.progress if task.progress > 0 else float('inf'))
                    )
                    delay_hours = (expected_completion_at_current_rate - task.deadline).total_seconds() / 3600
                    metrics["delay_duration"] = max(0, delay_hours)
                    
                    # Determine delay impact
                    if delay_hours > 40:  # More than a work week
                        metrics["delay_impact"] = "critical"
                        metrics["recovery_possible"] = False
                    elif delay_hours > 16:  # More than 2 work days
                        metrics["delay_impact"] = "high"
                    elif delay_hours > 8:  # More than 1 work day
                        metrics["delay_impact"] = "medium"
                    else:
                        metrics["delay_impact"] = "low"
                    
                    # Suggest recovery actions
                    if metrics["recovery_possible"]:
                        required_daily_progress = (100 - task.progress) / (task.deadline - now).days if task.deadline > now else float('inf')
                        metrics["suggested_actions"].append({
                            "type": "increase_progress",
                            "required_daily_progress": required_daily_progress,
                            "feasibility": "high" if required_daily_progress < 20 else "medium" if required_daily_progress < 40 else "low"
                        })
            
            return metrics
        except:
            return {"is_delayed": False, "delay_impact": "unknown"}

    def _calculate_resource_metrics(self, db: Session, task: Task) -> Dict[str, Any]:
        """Calculate detailed resource metrics"""
        try:
            metrics = {
                "resource_utilization": 0,
                "overload_risk": "low",
                "concurrent_tasks": 0,
                "resource_availability": 100,
                "bottlenecks": [],
                "expertise_match": None,
                "skill_gaps": []
            }
            
            if task.assigned_to:
                # Get user and their expertise
                user = db.query(User).filter(User.id == task.assigned_to).first()
                if user:
                    # Analyze expertise match
                    expertise_match = self._analyze_expertise_match(task, user)
                    metrics["expertise_match"] = expertise_match
                    
                    # Identify skill gaps
                    skill_gaps = self._identify_skill_gaps(task, user)
                    if skill_gaps:
                        metrics["skill_gaps"] = skill_gaps
                
                # Get all active tasks for this resource
                concurrent_tasks = db.query(Task).filter(
                    Task.assigned_to == task.assigned_to,
                    Task.state == "in_progress"
                ).all()
                
                metrics["concurrent_tasks"] = len(concurrent_tasks)
                
                # Calculate total allocated hours
                total_allocated_hours = sum(t.planned_hours or 0 for t in concurrent_tasks)
                available_hours = 40  # Assuming 40-hour work week
                
                metrics["resource_utilization"] = (total_allocated_hours / available_hours) * 100
                
                # Determine overload risk
                if metrics["resource_utilization"] > 100:
                    metrics["overload_risk"] = "critical"
                    metrics["resource_availability"] = 0
                elif metrics["resource_utilization"] > 80:
                    metrics["overload_risk"] = "high"
                    metrics["resource_availability"] = 100 - metrics["resource_utilization"]
                elif metrics["resource_utilization"] > 60:
                    metrics["overload_risk"] = "medium"
                    metrics["resource_availability"] = 100 - metrics["resource_utilization"]
                
                # Identify bottlenecks
                if metrics["overload_risk"] != "low":
                    metrics["bottlenecks"].append({
                        "type": "resource_overallocation",
                        "details": {
                            "allocated_hours": total_allocated_hours,
                            "available_hours": available_hours,
                            "concurrent_tasks": [{"id": t.id, "name": t.name} for t in concurrent_tasks]
                        }
                    })
                
                # Add expertise-based bottlenecks
                if metrics["expertise_match"] and metrics["expertise_match"]["match_percentage"] < 50:
                    metrics["bottlenecks"].append({
                        "type": "expertise_mismatch",
                        "details": {
                            "match_percentage": metrics["expertise_match"]["match_percentage"],
                            "missing_skills": metrics["skill_gaps"]
                        }
                    })
            
            return metrics
        except:
            return {"resource_utilization": 0, "overload_risk": "unknown"}

    def _analyze_expertise_match(self, task: Task, user: User) -> Dict[str, Any]:
        """Analyze how well the user's expertise matches the task requirements"""
        try:
            # Extract task requirements from task name and description
            task_text = f"{task.name} {task.description or ''}"
            task_text = task_text.lower()
            
            # Initialize match metrics
            matches = []
            total_relevant_skills = 0
            
            # Check expertise match
            if user.expertise:
                for exp in user.expertise:
                    if exp.lower() in task_text:
                        matches.append({"type": "expertise", "skill": exp})
                        total_relevant_skills += 1
            
            # Check skills match
            if user.skills:
                for skill in user.skills:
                    if skill.lower() in task_text:
                        matches.append({"type": "skill", "skill": skill})
                        total_relevant_skills += 1
            
            # Check specializations match
            if user.specializations:
                for spec in user.specializations:
                    if spec.lower() in task_text:
                        matches.append({"type": "specialization", "skill": spec})
                        total_relevant_skills += 1
            
            # Calculate match percentage
            match_percentage = (len(matches) / max(1, total_relevant_skills)) * 100 if total_relevant_skills > 0 else 0
            
            return {
                "match_percentage": match_percentage,
                "matching_skills": matches,
                "experience_level": user.experience_level,
                "relevant_certifications": [cert for cert in (user.certifications or []) 
                                         if cert.lower() in task_text]
            }
        except:
            return {"match_percentage": 0, "matching_skills": []}

    def _identify_skill_gaps(self, task: Task, user: User) -> List[Dict[str, Any]]:
        """Identify potential skill gaps for the task"""
        try:
            skill_gaps = []
            
            # Extract task requirements
            task_text = f"{task.name} {task.description or ''}"
            task_text = task_text.lower()
            
            # Common technical skills to check for
            common_skills = {
                "frontend": ["react", "vue", "angular", "javascript", "css", "html"],
                "backend": ["python", "java", "node", "api", "database"],
                "devops": ["aws", "docker", "kubernetes", "ci/cd", "deployment"],
                "database": ["sql", "postgresql", "mongodb", "redis"],
                "mobile": ["ios", "android", "react native", "flutter"],
                "ai": ["machine learning", "python", "tensorflow", "pytorch"]
            }
            
            # Check for skill gaps in each category
            user_skills = set(s.lower() for s in (user.skills or []))
            user_expertise = set(e.lower() for e in (user.expertise or []))
            user_specializations = set(s.lower() for s in (user.specializations or []))
            all_user_skills = user_skills.union(user_expertise).union(user_specializations)
            
            for category, skills in common_skills.items():
                category_relevant = any(skill in task_text for skill in skills)
                if category_relevant:
                    missing_skills = [
                        skill for skill in skills 
                        if skill in task_text and skill not in all_user_skills
                    ]
                    if missing_skills:
                        skill_gaps.append({
                            "category": category,
                            "missing_skills": missing_skills
                        })
            
            return skill_gaps
        except:
            return []

    def _calculate_completion_metrics(self, task: Task) -> Dict[str, Any]:
        """Calculate detailed completion metrics"""
        try:
            metrics = {
                "estimated_completion_date": None,
                "completion_confidence": "high",
                "completion_trend": "on_track",
                "velocity_metrics": {},
                "blocking_factors": []
            }
            
            if task.metrics and task.progress > 0:
                # Calculate velocity (progress per day)
                days_active = (datetime.utcnow() - task.start_date).days if task.start_date else 1
                velocity = task.progress / max(1, days_active)
                
                # Calculate estimated completion
                remaining_progress = 100 - task.progress
                days_to_completion = remaining_progress / velocity if velocity > 0 else float('inf')
                
                if days_to_completion != float('inf'):
                    metrics["estimated_completion_date"] = (
                        datetime.utcnow() + timedelta(days=days_to_completion)
                    ).isoformat()
                
                # Calculate velocity metrics
                metrics["velocity_metrics"] = {
                    "current_velocity": velocity,
                    "required_velocity": (100 - task.progress) / max(1, (task.deadline - datetime.utcnow()).days) if task.deadline else 0,
                    "trend": "increasing" if task.metrics.time_estimate_accuracy > 1 else "decreasing"
                }
                
                # Determine completion confidence
                if task.deadline:
                    estimated_completion = datetime.utcnow() + timedelta(days=days_to_completion)
                    buffer_days = (task.deadline - estimated_completion).days
                    
                    if buffer_days < 0:
                        metrics["completion_confidence"] = "low"
                        metrics["completion_trend"] = "at_risk"
                    elif buffer_days < 2:
                        metrics["completion_confidence"] = "medium"
                        metrics["completion_trend"] = "tight"
                
                # Identify blocking factors
                if task.metrics.idle_time > 16:  # More than 2 work days idle
                    metrics["blocking_factors"].append({
                        "type": "high_idle_time",
                        "idle_hours": task.metrics.idle_time
                    })
                
                if task.metrics.rework_hours > task.metrics.actual_duration * 0.2:  # More than 20% rework
                    metrics["blocking_factors"].append({
                        "type": "high_rework",
                        "rework_percentage": (task.metrics.rework_hours / task.metrics.actual_duration) * 100
                    })
            
            return metrics
        except:
            return {"completion_confidence": "unknown"}

    def _calculate_risk_metrics(self, db: Session, task: Task) -> Dict[str, Any]:
        """Calculate detailed risk metrics"""
        try:
            metrics = {
                "overall_risk_score": 0,
                "risk_factors": [],
                "warning_signs": [],
                "mitigation_suggestions": []
            }
            
            risk_score = 0
            
            # Check deadline risk
            if task.deadline:
                days_to_deadline = (task.deadline - datetime.utcnow()).days
                if days_to_deadline < 0:
                    risk_score += 5
                    metrics["risk_factors"].append({
                        "type": "overdue",
                        "severity": "critical",
                        "days_overdue": abs(days_to_deadline)
                    })
                elif days_to_deadline < 2:
                    risk_score += 3
                    metrics["risk_factors"].append({
                        "type": "tight_deadline",
                        "severity": "high",
                        "days_remaining": days_to_deadline
                    })
            
            # Check progress risk
            if task.progress < 20 and task.start_date and (datetime.utcnow() - task.start_date).days > 5:
                risk_score += 4
                metrics["risk_factors"].append({
                    "type": "slow_progress",
                    "severity": "high",
                    "current_progress": task.progress
                })
            
            # Check resource risk
            if task.metrics and task.metrics.idle_time > 24:
                risk_score += 3
                metrics["risk_factors"].append({
                    "type": "high_idle_time",
                    "severity": "medium",
                    "idle_hours": task.metrics.idle_time
                })
            
            # Check dependency risk
            blocked_by = self._check_dependencies(db, task)
            if blocked_by["is_blocked"]:
                risk_score += len(blocked_by["blocked_by"]) * 2
                metrics["risk_factors"].append({
                    "type": "blocked_by_dependencies",
                    "severity": "high",
                    "blocking_tasks": blocked_by["blocked_by"]
                })
            
            # Calculate overall risk score (0-10 scale)
            metrics["overall_risk_score"] = min(10, risk_score)
            
            # Generate warning signs
            if metrics["overall_risk_score"] >= 7:
                metrics["warning_signs"].append({
                    "type": "critical_risk_level",
                    "message": "Task is at critical risk of failure",
                    "indicators": [f["type"] for f in metrics["risk_factors"]]
                })
            
            # Generate mitigation suggestions
            if metrics["risk_factors"]:
                for factor in metrics["risk_factors"]:
                    if factor["type"] == "overdue":
                        metrics["mitigation_suggestions"].append({
                            "type": "schedule_adjustment",
                            "action": "Consider breaking task into smaller subtasks",
                            "priority": "high"
                        })
                    elif factor["type"] == "blocked_by_dependencies":
                        metrics["mitigation_suggestions"].append({
                            "type": "dependency_resolution",
                            "action": "Escalate blocking dependencies to project manager",
                            "priority": "high"
                        })
            
            return metrics
        except:
            return {"overall_risk_score": 0, "risk_factors": []} 