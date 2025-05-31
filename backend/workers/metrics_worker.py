import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from services.precalculation_service import PreCalculationService
from models.task import Task
from models.project import Project

class MetricsWorker:
    def __init__(self):
        self.precalc_service = PreCalculationService()
        self._last_update = {}  # Track last update time for each entity
        self._changed_entities = set()  # Track which entities need immediate update
        
    async def start(self):
        """Start the metrics worker"""
        await asyncio.gather(
            self._regular_update_loop(),
            self._immediate_update_loop()
        )
    
    async def _regular_update_loop(self):
        """Regular update loop that runs every minute"""
        while True:
            try:
                db = SessionLocal()
                try:
                    # Update all projects
                    projects = db.query(Project).all()
                    for project in projects:
                        if not self._needs_immediate_update(f"project:{project.id}"):
                            await self.precalc_service.calculate_project_metrics(db, project.id)
                    
                    # Update all tasks
                    tasks = db.query(Task).all()
                    for task in tasks:
                        if not self._needs_immediate_update(f"task:{task.id}"):
                            await self.precalc_service.calculate_task_metrics(db, task.id)
                            
                finally:
                    db.close()
                    
                # Wait for 1 minute before next update
                await asyncio.sleep(60)
                
            except Exception as e:
                print(f"Error in metrics worker regular update: {str(e)}")
                await asyncio.sleep(5)  # Wait 5 seconds before retry on error
    
    async def _immediate_update_loop(self):
        """Immediate update loop for changed entities"""
        while True:
            try:
                if self._changed_entities:
                    db = SessionLocal()
                    try:
                        # Process all changed entities
                        entities = self._changed_entities.copy()
                        self._changed_entities.clear()
                        
                        for entity_key in entities:
                            entity_type, entity_id = entity_key.split(":")
                            entity_id = int(entity_id)
                            
                            if entity_type == "project":
                                await self.precalc_service.calculate_project_metrics(db, entity_id)
                            elif entity_type == "task":
                                await self.precalc_service.calculate_task_metrics(db, entity_id)
                                
                            # Update last update time
                            self._last_update[entity_key] = datetime.utcnow()
                            
                    finally:
                        db.close()
                
                # Small sleep to prevent CPU overuse
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"Error in metrics worker immediate update: {str(e)}")
                await asyncio.sleep(1)
    
    def mark_entity_changed(self, entity_type: str, entity_id: int):
        """Mark an entity as changed to trigger immediate update"""
        entity_key = f"{entity_type}:{entity_id}"
        self._changed_entities.add(entity_key)
    
    def _needs_immediate_update(self, entity_key: str) -> bool:
        """Check if an entity needs immediate update"""
        return entity_key in self._changed_entities

# Global instance
metrics_worker = MetricsWorker()

async def start_metrics_worker():
    """Start the metrics worker"""
    await metrics_worker.start() 