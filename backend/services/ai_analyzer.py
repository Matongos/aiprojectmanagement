from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional

from database import SessionLocal
from models.time_entry import TimeEntry
from models.task import Task
from services.ollama_service import get_ollama_client

async def analyze_time_entry(entry_id: int) -> Dict:
    """
    Analyze a time entry using AI to generate insights and recommendations.
    This function uses the Ollama service to process the time entry data.
    """
    db = SessionLocal()
    try:
        # Get time entry and related data
        entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
        if not entry:
            return {}
            
        task = db.query(Task).filter(Task.id == entry.task_id).first()
        
        # Prepare context for AI analysis
        context = {
            "duration": entry.duration,
            "activity_type": entry.activity_type,
            "description": entry.description,
            "task_name": task.name if task else None,
            "task_priority": task.priority if task else None,
            "is_billable": entry.is_billable,
            "start_time": entry.start_time.isoformat() if entry.start_time else None,
            "end_time": entry.end_time.isoformat() if entry.end_time else None
        }
        
        # Get similar time entries for pattern analysis
        similar_entries = get_similar_entries(db, entry)
        
        # Calculate baseline metrics
        baseline_metrics = calculate_baseline_metrics(similar_entries)
        
        # Prepare prompt for AI analysis
        prompt = f"""
        Analyze this time entry and provide insights:
        
        Time Entry Details:
        - Duration: {entry.duration} hours
        - Activity: {entry.activity_type}
        - Description: {entry.description}
        - Task: {task.name if task else 'Unknown'}
        - Priority: {task.priority if task else 'Unknown'}
        
        Baseline Metrics:
        - Average duration for similar tasks: {baseline_metrics['avg_duration']}
        - Typical productivity patterns: {baseline_metrics['productivity_patterns']}
        
        Please provide:
        1. Productivity score (0-1)
        2. Efficiency metrics
        3. Recommendations for improvement
        4. Pattern analysis
        """
        
        # Get AI analysis from Ollama
        ollama = get_ollama_client()
        response = await ollama.generate(
            model="codellama",
            prompt=prompt,
            stream=False
        )
        
        # Process AI response
        try:
            analysis = json.loads(response.text)
        except:
            analysis = {
                "productivity_score": calculate_productivity_score(entry, baseline_metrics),
                "efficiency_metrics": {
                    "duration_ratio": entry.duration / baseline_metrics['avg_duration'] if baseline_metrics['avg_duration'] > 0 else 1,
                    "time_of_day_efficiency": calculate_time_of_day_efficiency(entry),
                    "context_switches": count_context_switches(entry, db)
                },
                "recommendations": generate_default_recommendations(entry, baseline_metrics),
                "patterns": identify_patterns(entry, similar_entries)
            }
        
        # Update time entry with AI insights
        entry.productivity_score = analysis.get("productivity_score", 0)
        entry.efficiency_metrics = json.dumps(analysis.get("efficiency_metrics", {}))
        db.commit()
        
        return analysis
        
    finally:
        db.close()

def get_similar_entries(db: Session, entry: TimeEntry) -> List[TimeEntry]:
    """Get similar time entries for comparison"""
    return db.query(TimeEntry).filter(
        TimeEntry.user_id == entry.user_id,
        TimeEntry.activity_type == entry.activity_type,
        TimeEntry.id != entry.id
    ).order_by(TimeEntry.created_at.desc()).limit(10).all()

def calculate_baseline_metrics(entries: List[TimeEntry]) -> Dict:
    """Calculate baseline metrics from similar entries"""
    if not entries:
        return {
            "avg_duration": 0,
            "productivity_patterns": []
        }
    
    return {
        "avg_duration": sum(e.duration for e in entries) / len(entries),
        "productivity_patterns": analyze_productivity_patterns(entries)
    }

def analyze_productivity_patterns(entries: List[TimeEntry]) -> List[Dict]:
    """Analyze productivity patterns from historical entries"""
    patterns = []
    for entry in entries:
        if entry.productivity_score:
            patterns.append({
                "time_of_day": entry.start_time.hour if entry.start_time else None,
                "duration": entry.duration,
                "score": entry.productivity_score
            })
    return patterns

def calculate_productivity_score(entry: TimeEntry, baseline: Dict) -> float:
    """Calculate a productivity score based on various factors"""
    score = 1.0
    
    # Duration factor
    if baseline["avg_duration"] > 0:
        duration_ratio = entry.duration / baseline["avg_duration"]
        if duration_ratio > 1.5 or duration_ratio < 0.5:
            score *= 0.8
    
    # Time of day factor
    if entry.start_time:
        hour = entry.start_time.hour
        if 9 <= hour <= 11 or 14 <= hour <= 16:  # Peak productivity hours
            score *= 1.2
        elif hour < 6 or hour > 22:  # Off hours
            score *= 0.7
    
    # Description quality
    if entry.description and len(entry.description) > 20:
        score *= 1.1
    
    return min(1.0, score)

def calculate_time_of_day_efficiency(entry: TimeEntry) -> float:
    """Calculate efficiency based on time of day"""
    if not entry.start_time:
        return 0.5
        
    hour = entry.start_time.hour
    if 9 <= hour <= 11:  # Morning peak
        return 1.0
    elif 14 <= hour <= 16:  # Afternoon peak
        return 0.9
    elif 6 <= hour <= 8 or 17 <= hour <= 19:  # Transition hours
        return 0.7
    else:  # Off hours
        return 0.5

def count_context_switches(entry: TimeEntry, db: Session) -> int:
    """Count potential context switches during the time period"""
    if not entry.start_time or not entry.end_time:
        return 0
        
    return db.query(TimeEntry).filter(
        TimeEntry.user_id == entry.user_id,
        TimeEntry.start_time.between(entry.start_time, entry.end_time),
        TimeEntry.id != entry.id
    ).count()

def generate_default_recommendations(entry: TimeEntry, baseline: Dict) -> List[str]:
    """Generate default recommendations based on entry analysis"""
    recommendations = []
    
    if baseline["avg_duration"] > 0:
        duration_ratio = entry.duration / baseline["avg_duration"]
        if duration_ratio > 1.3:
            recommendations.append("Consider breaking this task into smaller chunks")
        elif duration_ratio < 0.7:
            recommendations.append("You completed this faster than usual - document your approach")
    
    if entry.start_time:
        hour = entry.start_time.hour
        if hour < 6 or hour > 22:
            recommendations.append("Consider scheduling this work during core hours")
    
    if not entry.description:
        recommendations.append("Add a description to improve task tracking")
    
    return recommendations

def identify_patterns(entry: TimeEntry, similar_entries: List[TimeEntry]) -> Dict:
    """Identify patterns in time entry behavior"""
    patterns = {
        "time_of_day": {},
        "duration_clusters": {},
        "productivity_correlation": {}
    }
    
    # Analyze time of day patterns
    for e in similar_entries:
        if e.start_time:
            hour = e.start_time.hour
            period = f"{hour:02d}:00"
            patterns["time_of_day"][period] = patterns["time_of_day"].get(period, 0) + 1
    
    # Analyze duration clusters
    for e in similar_entries:
        duration_range = f"{int(e.duration)}h"
        patterns["duration_clusters"][duration_range] = patterns["duration_clusters"].get(duration_range, 0) + 1
    
    # Analyze productivity correlation
    for e in similar_entries:
        if e.productivity_score:
            score_range = f"{int(e.productivity_score * 10)}/10"
            patterns["productivity_correlation"][score_range] = patterns["productivity_correlation"].get(score_range, 0) + 1
    
    return patterns 