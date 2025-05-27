from typing import Any
from sqlalchemy.orm import Session
from .metrics_collector import MetricsCollector

class MetricsEventHandler:
    def __init__(self, db: Session):
        self.db = db
        self.metrics_collector = MetricsCollector(db)

    async def handle_project_update(self, project_id: int, event_type: str, data: Any = None):
        """Handle project-related events"""
        # Collect project metrics
        await self.metrics_collector.collect_project_metrics(project_id)
        
        # If milestone related, update milestone metrics
        if event_type in ['milestone_created', 'milestone_completed', 'milestone_updated']:
            # Additional milestone-specific metric collection
            pass

    async def handle_task_update(self, task_id: int, project_id: int, event_type: str, data: Any = None):
        """Handle task-related events"""
        # Collect task metrics
        await self.metrics_collector.collect_task_metrics(task_id)
        
        # Update project metrics as task changes affect project metrics
        await self.metrics_collector.collect_project_metrics(project_id)

    async def handle_resource_update(self, user_id: int, project_id: int, event_type: str, data: Any = None):
        """Handle resource-related events"""
        # Collect resource metrics
        await self.metrics_collector.collect_resource_metrics(user_id, project_id)
        
        # Update project metrics as resource changes affect project metrics
        await self.metrics_collector.collect_project_metrics(project_id)

    async def handle_activity_log(self, activity_type: str, entity_id: int, entity_type: str, user_id: int = None):
        """Handle activity log events"""
        if entity_type == 'project':
            await self.handle_project_update(entity_id, activity_type)
        elif entity_type == 'task':
            # Get project_id from task
            project_id = await self._get_project_id_from_task(entity_id)
            await self.handle_task_update(entity_id, project_id, activity_type)
        elif entity_type == 'resource':
            # Get project_id from context
            project_id = await self._get_project_id_from_context(entity_id)
            await self.handle_resource_update(entity_id, project_id, activity_type)

    async def _get_project_id_from_task(self, task_id: int) -> int:
        """Helper method to get project_id from task"""
        # Implementation to fetch project_id from task
        pass

    async def _get_project_id_from_context(self, context_id: int) -> int:
        """Helper method to get project_id from context"""
        # Implementation to fetch project_id from context
        pass 