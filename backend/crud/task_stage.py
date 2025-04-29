from typing import List, Optional
from sqlalchemy.orm import Session
from models.task_stage import TaskStage
from schemas.task_stage import TaskStageCreate, TaskStageUpdate
from crud.base import CRUDBase
from sqlalchemy import desc

class CRUDTaskStage(CRUDBase[TaskStage, TaskStageCreate, TaskStageUpdate]):
    def get_project_stages(
        self, db: Session, *, project_id: int
    ) -> List[TaskStage]:
        """Get all stages for a specific project ordered by sequence."""
        return (
            db.query(self.model)
            .filter(TaskStage.project_id == project_id)
            .order_by(TaskStage.sequence_order)
            .all()
        )

    def create_stage(
        self, db: Session, *, obj_in: TaskStageCreate
    ) -> TaskStage:
        """Create a new stage and set its sequence order."""
        # Get the highest sequence order for the project
        last_stage = (
            db.query(self.model)
            .filter(TaskStage.project_id == obj_in.project_id)
            .order_by(desc(TaskStage.sequence_order))
            .first()
        )
        
        # Set the sequence order to be one more than the highest
        sequence_order = (last_stage.sequence_order + 1) if last_stage else 0
        
        db_obj = TaskStage(
            name=obj_in.name,
            description=obj_in.description,
            project_id=obj_in.project_id,
            sequence_order=sequence_order
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_sequence(
        self, db: Session, *, stage_id: int, new_sequence: int, project_id: int
    ) -> TaskStage:
        """Update the sequence order of a stage and reorder other stages as needed."""
        # Get the stage to update
        stage = db.query(self.model).filter(TaskStage.id == stage_id).first()
        if not stage:
            return None
            
        old_sequence = stage.sequence_order
        
        # Update other stages' sequence orders
        if new_sequence > old_sequence:
            # Moving forward: decrease sequence of stages in between
            db.query(self.model).filter(
                TaskStage.project_id == project_id,
                TaskStage.sequence_order > old_sequence,
                TaskStage.sequence_order <= new_sequence
            ).update({"sequence_order": TaskStage.sequence_order - 1})
        else:
            # Moving backward: increase sequence of stages in between
            db.query(self.model).filter(
                TaskStage.project_id == project_id,
                TaskStage.sequence_order >= new_sequence,
                TaskStage.sequence_order < old_sequence
            ).update({"sequence_order": TaskStage.sequence_order + 1})
        
        # Update the stage's sequence
        stage.sequence_order = new_sequence
        db.commit()
        db.refresh(stage)
        return stage

task_stage = CRUDTaskStage(TaskStage) 