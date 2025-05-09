from typing import List, Optional
from sqlalchemy.orm import Session
from models.task_stage import TaskStage
from models.task import Task
from schemas.task_stage import TaskStageCreate, TaskStageUpdate
from crud.base import CRUDBase
from sqlalchemy import desc

class CRUDTaskStage(CRUDBase[TaskStage, TaskStageCreate, TaskStageUpdate]):
    def get_project_stages(
        self, db: Session, *, project_id: int
    ) -> List[TaskStage]:
        """Get all stages for a specific project ordered by sequence."""
        stages = (
            db.query(self.model)
            .filter(TaskStage.project_id == project_id)
            .order_by(TaskStage.sequence)
            .all()
        )
        
        # For each stage, serialize its tasks' assignees and ensure progress is valid
        for stage in stages:
            if stage.tasks:
                for task in stage.tasks:
                    # Handle assignee serialization
                    if task.assignee:
                        task.assignee = {
                            'id': task.assignee.id,
                            'username': task.assignee.username,
                            'email': task.assignee.email,
                            'full_name': task.assignee.full_name,
                            'profile_image_url': task.assignee.profile_image_url
                        }
                    # Ensure progress is a valid float
                    if task.progress is None:
                        task.progress = 0.0
        
        return stages

    def create_stage(
        self, db: Session, *, obj_in: TaskStageCreate
    ) -> TaskStage:
        """Create a new stage and set its sequence."""
        # Get the highest sequence for the project
        last_stage = (
            db.query(self.model)
            .filter(TaskStage.project_id == obj_in.project_id)
            .order_by(desc(TaskStage.sequence))
            .first()
        )
        
        # Set the sequence to be one more than the highest, or 1 if no stages exist
        sequence = (last_stage.sequence + 1) if last_stage else 1
        
        db_obj = TaskStage(
            name=obj_in.name,
            description=obj_in.description,
            project_id=obj_in.project_id,
            sequence=sequence
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_sequence(
        self, db: Session, *, stage_id: int, new_sequence: int, project_id: int
    ) -> TaskStage:
        """Update the sequence of a stage and reorder other stages as needed."""
        # Get the stage to update
        stage = db.query(self.model).filter(TaskStage.id == stage_id).first()
        if not stage:
            return None
            
        old_sequence = stage.sequence
        
        # Update other stages' sequences
        if new_sequence > old_sequence:
            # Moving forward: decrease sequence of stages in between
            db.query(self.model).filter(
                TaskStage.project_id == project_id,
                TaskStage.sequence > old_sequence,
                TaskStage.sequence <= new_sequence
            ).update({"sequence": TaskStage.sequence - 1})
        else:
            # Moving backward: increase sequence of stages in between
            db.query(self.model).filter(
                TaskStage.project_id == project_id,
                TaskStage.sequence >= new_sequence,
                TaskStage.sequence < old_sequence
            ).update({"sequence": TaskStage.sequence + 1})
        
        # Update the stage's sequence
        stage.sequence = new_sequence
        db.commit()
        db.refresh(stage)
        return stage

    def get_stage(self, db: Session, stage_id: int) -> Optional[TaskStage]:
        """Get a task stage by ID"""
        return db.query(self.model).filter(self.model.id == stage_id).first()

    def update_stage(self, db: Session, *, db_obj: TaskStage, obj_in: TaskStageUpdate) -> TaskStage:
        """Update a task stage"""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete_stage(self, db: Session, *, stage_id: int) -> TaskStage:
        """Delete a task stage"""
        # Get the stage to delete
        stage = db.query(self.model).get(stage_id)
        if not stage:
            return None

        # Get the default "Inbox" stage for this project
        inbox_stage = (
            db.query(self.model)
            .filter(
                TaskStage.project_id == stage.project_id,
                TaskStage.name == "Inbox"
            )
            .first()
        )

        if inbox_stage:
            # Move all tasks in this stage to the Inbox stage
            db.query(Task).filter(Task.stage_id == stage_id).update(
                {"stage_id": inbox_stage.id},
                synchronize_session=False
            )

        # Update sequences of remaining stages
        db.query(self.model).filter(
            TaskStage.project_id == stage.project_id,
            TaskStage.sequence > stage.sequence
        ).update(
            {"sequence": TaskStage.sequence - 1},
            synchronize_session=False
        )

        # Delete the stage
        db.delete(stage)
        db.commit()
        return stage

    def reorder_stages(self, db: Session, project_id: int, stage_order: List[int]) -> List[TaskStage]:
        """Reorder stages in a project"""
        stages = self.get_project_stages(db, project_id)
        stage_dict = {stage.id: stage for stage in stages}
        
        for sequence, stage_id in enumerate(stage_order, 1):
            if stage_id in stage_dict:
                stage_dict[stage_id].sequence = sequence
        
        db.commit()
        return self.get_project_stages(db, project_id)

task_stage = CRUDTaskStage(TaskStage) 