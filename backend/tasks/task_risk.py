from celery_app import celery_app
from sqlalchemy.orm import sessionmaker
from database import engine
from services.ai_service import AIService
from models.task import Task
import logging
import asyncio

logger = logging.getLogger(__name__)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery_app.task(bind=True)
def calculate_task_risk_analysis_task(self, task_id):
    """
    Celery task to calculate complete risk analysis for a task.
    
    This task:
    1. Performs comprehensive AI risk analysis
    2. Calculates weighted component scores
    3. Stores results in TaskRisk table
    4. Returns complete analysis with component breakdown
    
    Component weights:
    - Time sensitivity: 30 points (30%)
    - Complexity: 20 points (20%)
    - Priority: 20 points (20%)
    - Role match: 20 points (20%)
    - Dependencies: 10 points (10%)
    - Comments: 10 points (10%)
    """
    db = SessionLocal()
    try:
        # Import models here to avoid circular imports
        from models.user import User
        from models.notification import Notification
        from models.log_note_attachment import LogNoteAttachment
        from crud.task_risk import TaskRiskCRUD
        
        # Check if task exists
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {
                "success": False, 
                "message": f"Task {task_id} not found",
                "task_id": task_id
            }
        
        # Check if task is completed or cancelled
        if task.state in ['done', 'cancelled']:
            return {
                "success": True,
                "task_id": task_id,
                "risk_score": 0,
                "risk_level": "minimal",
                "message": f"Task is {task.state}, risk analysis not needed",
                "status": f"Task is {task.state}"
            }
        
        # Create AI service instance
        ai_service = AIService(db)
        
        # Update task state to show progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 1,
                'total': 6,
                'status': 'Starting risk analysis...'
            }
        )
        
        # Step 1: Collect all risk data
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 1,
                'total': 6,
                'status': 'Collecting risk data...'
            }
        )
        
        # Call the async function properly
        risk_data = asyncio.run(ai_service.analyze_task_risk(task_id))
        
        if "error" in risk_data:
            return {
                "success": False,
                "message": f"Error collecting risk data: {risk_data['error']}",
                "task_id": task_id
            }
        
        collected_data = risk_data.get("collected_data", {})
        
        # Step 2: Extract component scores
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 2,
                'total': 6,
                'status': 'Calculating component scores...'
            }
        )
        
        time_risk_data = collected_data.get("time_risk_analysis", {})
        complexity_data = collected_data.get("task_complexity", {})
        assigned_person_data = collected_data.get("assigned_person", {})
        dependency_data = collected_data.get("task_dependencies", {})
        comments_data = collected_data.get("comments_analysis", {})
        task_details = collected_data.get("task_details", {})
        
        # Step 3: Calculate component scores
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 3,
                'total': 6,
                'status': 'Processing time sensitivity...'
            }
        )
        
        # Get time sensitivity score - calculate if not available
        cached_time_risk = time_risk_data.get("cached_time_risk")
        
        if cached_time_risk and cached_time_risk.get("time_risk_percentage") is not None:
            # Use cached time risk data
            time_risk_percentage = cached_time_risk.get('time_risk_percentage', 0)
            time_sensitivity_score = (time_risk_percentage / 100) * 35
            time_risk_source = "cached"
        else:
            # Calculate time risk on-demand
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': 3,
                    'total': 6,
                    'status': 'Calculating time risk on-demand...'
                }
            )
            
            # Call the time risk calculation directly
            calculated_time_risk = asyncio.run(ai_service._analyze_time_risks(task))
            
            if calculated_time_risk and calculated_time_risk.get("time_risk_percentage") is not None:
                time_risk_percentage = calculated_time_risk.get('time_risk_percentage', 0)
                time_sensitivity_score = (time_risk_percentage / 100) * 35
                time_risk_source = "calculated"
                
                # Store the calculated result in cache
                try:
                    ai_service.store_time_risk_cache(task_id, calculated_time_risk, expiration_seconds=3600)
                except Exception as cache_error:
                    logger.warning(f"Failed to cache time risk: {str(cache_error)}")
            else:
                # If calculation still fails, raise an error instead of using default
                raise ValueError(f"Unable to calculate time risk for task {task_id}. Time risk calculation failed.")
        
        logger.info(f"Time sensitivity score: {time_sensitivity_score} (source: {time_risk_source})")
        
        # Handle complexity score conversion properly
        raw_complexity_score = complexity_data.get("complexity_score", 0)
        if isinstance(raw_complexity_score, (int, float)):
            complexity_score = (raw_complexity_score / 100) * 25  # Convert to 25-point scale
        else:
            complexity_score = 12.5  # Default medium complexity (50% of 25)
        
        # Priority score removed - no longer included in calculation
        priority_score = 0
        
        role_match_score = assigned_person_data.get("total_score", 0)  # Already out of 20
        
        # Handle dependency score conversion properly - fix to 10-point scale
        raw_dependency_score = dependency_data.get("dependency_score", 0)
        if isinstance(raw_dependency_score, (int, float)):
            dependency_score = raw_dependency_score  # Already on 0-10 scale
        else:
            dependency_score = 0.0  # Default no dependency risk
        
        comments_score = comments_data.get("communication_score", 5)  # Already out of 10
        
        # Step 4: Calculate final weighted risk score (now out of 100 with new weights)
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 4,
                'total': 6,
                'status': 'Computing final risk score...'
            }
        )
        
        final_risk_score = (
            time_sensitivity_score +
            complexity_score +
            priority_score +  # Will be 0
            role_match_score +
            dependency_score +
            comments_score
        )
        
        # Determine risk level based on final score
        if final_risk_score >= 80:
            risk_level = "extreme"
        elif final_risk_score >= 60:
            risk_level = "critical"
        elif final_risk_score >= 40:
            risk_level = "high"
        elif final_risk_score >= 20:
            risk_level = "medium"
        elif final_risk_score >= 10:
            risk_level = "low"
        else:
            risk_level = "minimal"
        
        # Step 5: Prepare risk factors and recommendations
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 5,
                'total': 6,
                'status': 'Generating recommendations...'
            }
        )
        
        risk_factors = {
            "time_sensitivity": {
                "score": time_sensitivity_score,
                "details": time_risk_data.get("cached_time_risk", {}),
                "risk_level": time_risk_data.get("risk_level", "medium"),
                "source": time_risk_source
            },
            "complexity": {
                "score": complexity_score,
                "details": complexity_data,
                "risk_level": "high" if complexity_score > 12.5 else "medium" if complexity_score > 6.25 else "low"
            },
            "role_match": {
                "score": role_match_score,
                "details": assigned_person_data.get("ai_analysis", {}),
                "risk_level": "high" if role_match_score > 10 else "medium" if role_match_score > 5 else "low"
            },
            "dependencies": {
                "score": dependency_score,
                "details": dependency_data.get("ai_analysis", {}),
                "risk_level": dependency_data.get("dependency_risk_level", "low")
            },
            "comments": {
                "score": comments_score,
                "details": comments_data,
                "risk_level": "high" if comments_score > 5 else "medium" if comments_score > 2 else "low"
            }
        }
        
        # Generate recommendations
        recommendations = {
            "immediate_actions": [],
            "short_term": [],
            "long_term": []
        }
        
        # Time-based recommendations
        if time_sensitivity_score > 25:
            recommendations["immediate_actions"].append("Review task timeline and consider deadline extension")
        elif time_sensitivity_score > 17.5:
            recommendations["short_term"].append("Monitor task progress closely")
        
        # Complexity recommendations
        if complexity_score > 12.5:
            recommendations["immediate_actions"].append("Break down complex task into smaller subtasks")
        
        # Role match recommendations
        if role_match_score > 15:
            recommendations["immediate_actions"].append("Consider reassigning task to better-suited team member")
        elif role_match_score > 10:
            recommendations["short_term"].append("Provide additional training or support to assigned team member")
        
        # Dependency recommendations
        if dependency_score > 5:
            recommendations["short_term"].append("Review and resolve task dependencies")
        
        # Comments recommendations
        if comments_score > 5:
            recommendations["short_term"].append("Improve communication and collaboration on this task")
        
        # Step 6: Store in database
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 6,
                'total': 6,
                'status': 'Storing results in database...'
            }
        )
        
        # Serialize datetime objects for JSON storage
        serialized_risk_factors = ai_service._serialize_datetime_objects(risk_factors)
        serialized_recommendations = ai_service._serialize_datetime_objects(recommendations)
        serialized_metrics = ai_service._serialize_datetime_objects(collected_data.get("metrics"))
        
        # Try to store in database, but don't fail if it doesn't work
        stored_risk = None
        database_record_id = None
        stored_in_database = False
        
        try:
            task_risk_crud = TaskRiskCRUD(db)
            stored_risk = task_risk_crud.create_risk_analysis(
                task_id=task_id,
                risk_score=final_risk_score,
                risk_level=risk_level,
                time_sensitivity=time_sensitivity_score,
                complexity=complexity_score,
                priority=0,  # Set to 0 since priority is no longer used
                risk_factors=serialized_risk_factors,
                recommendations=serialized_recommendations,
                metrics=serialized_metrics
            )
            database_record_id = stored_risk.id
            stored_in_database = True
            logger.info(f"Successfully stored risk analysis in database with ID: {database_record_id}")
        except Exception as db_error:
            logger.warning(f"Failed to store risk analysis in database: {str(db_error)}")
            logger.warning("Continuing with analysis results without database storage")
            stored_in_database = False
        
        # Return complete analysis
        result = {
            "success": True,
            "task_id": task_id,
            "analysis_timestamp": ai_service._get_current_time().isoformat(),
            "risk_score": round(final_risk_score, 2),
            "risk_level": risk_level,
            
            # Component scores
            "time_sensitivity": round(time_sensitivity_score, 2),
            "time_sensitivity_source": time_risk_source,
            "complexity": round(complexity_score, 2),
            "role_match": round(role_match_score, 2),
            "dependencies": round(dependency_score, 2),
            "comments": round(comments_score, 2),
            
            # Detailed analysis
            "risk_factors": risk_factors,
            "recommendations": recommendations,
            "metrics": collected_data.get("metrics"),
            
            # Analysis metadata
            "analysis_version": "1.0",
            "calculation_method": "weighted_component_analysis",
            "stored_in_database": stored_in_database,
            "database_record_id": database_record_id,
            
            # Component breakdown
            "component_breakdown": {
                "time_sensitivity": {
                    "score": round(time_sensitivity_score, 2),
                    "weight": "35%",
                    "max_score": 35,
                    "source": time_risk_source
                },
                "complexity": {
                    "score": round(complexity_score, 2),
                    "weight": "25%",
                    "max_score": 25
                },
                "role_match": {
                    "score": round(role_match_score, 2),
                    "weight": "20%",
                    "max_score": 20
                },
                "dependencies": {
                    "score": round(dependency_score, 2),
                    "weight": "10%",
                    "max_score": 10
                },
                "comments": {
                    "score": round(comments_score, 2),
                    "weight": "10%",
                    "max_score": 10
                }
            },
            
            # Status
            "status": "completed",
            "message": "Risk analysis completed successfully"
        }
        
        return result
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error calculating risk analysis for task {task_id}: {str(e)}")
        logger.error(f"Error details: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False, 
            "message": f"Error calculating risk analysis: {str(e)}",
            "task_id": task_id
        }
    finally:
        db.close() 