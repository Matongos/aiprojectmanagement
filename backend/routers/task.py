from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
from database import get_db
from services.priority_service import PriorityService
from routers.auth import get_current_user

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    dependencies=[Depends(get_current_user)]
)

@router.put("/{task_id}/auto-priority")
async def auto_set_task_priority(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """
    Automatically calculate and set task priority using rules and AI.
    
    The priority is determined by:
    1. First applying rule-based logic for common cases
    2. Using AI for more nuanced decisions when rules are inconclusive
    3. Respecting manual priority if set
    
    Returns both rule-based and AI suggestions along with the final priority.
    """
    try:
        priority_service = PriorityService(db)
        result = await priority_service.calculate_priority(task_id)
        
        # Update task priority if not manually set
        if result["priority_source"] != "MANUAL":
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.priority = result["final_priority"]
                task.priority_source = result["priority_source"]
                db.commit()
        
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating task priority: {str(e)}"
        ) 