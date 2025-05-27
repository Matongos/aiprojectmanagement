"""add metrics tables

Revision ID: add_metrics_tables_006
Create Date: 2024-03-20 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision = 'add_metrics_tables_006'
down_revision = 'base_tables_001'  # Now depends on our base migration
branch_labels = None
depends_on = None

def upgrade():
    # Create project_metrics table
    op.create_table(
        'project_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('schedule_variance', sa.Float(), nullable=True),
        sa.Column('milestone_completion_rate', sa.Float(), nullable=True),
        sa.Column('budget_utilization', sa.Float(), nullable=True),
        sa.Column('cost_variance', sa.Float(), nullable=True),
        sa.Column('defect_density', sa.Float(), nullable=True),
        sa.Column('rework_rate', sa.Float(), nullable=True),
        sa.Column('velocity', sa.Float(), nullable=True),
        sa.Column('throughput', sa.Float(), nullable=True),
        sa.Column('resource_utilization', sa.Float(), nullable=True),
        sa.Column('team_load', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create task_metrics table
    op.create_table(
        'task_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('actual_duration', sa.Float(), nullable=True),
        sa.Column('time_estimate_accuracy', sa.Float(), nullable=True),
        sa.Column('idle_time', sa.Float(), nullable=True),
        sa.Column('review_iterations', sa.Integer(), nullable=True),
        sa.Column('bug_count', sa.Integer(), nullable=True),
        sa.Column('rework_hours', sa.Float(), nullable=True),
        sa.Column('complexity_score', sa.Float(), nullable=True),
        sa.Column('dependency_count', sa.Integer(), nullable=True),
        sa.Column('handover_count', sa.Integer(), nullable=True),
        sa.Column('comment_count', sa.Integer(), nullable=True),
        sa.Column('state_changes', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('blocked_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create resource_metrics table
    op.create_table(
        'resource_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('billable_hours', sa.Float(), nullable=True),
        sa.Column('availability_rate', sa.Float(), nullable=True),
        sa.Column('overtime_hours', sa.Float(), nullable=True),
        sa.Column('task_completion_rate', sa.Float(), nullable=True),
        sa.Column('average_task_duration', sa.Float(), nullable=True),
        sa.Column('productivity_score', sa.Float(), nullable=True),
        sa.Column('skill_utilization', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('learning_curve', sa.Float(), nullable=True),
        sa.Column('collaboration_score', sa.Float(), nullable=True),
        sa.Column('response_time', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('idx_project_metrics_project_id', 'project_metrics', ['project_id'])
    op.create_index('idx_task_metrics_task_id', 'task_metrics', ['task_id'])
    op.create_index('idx_resource_metrics_user_id', 'resource_metrics', ['user_id'])
    op.create_index('idx_resource_metrics_project_id', 'resource_metrics', ['project_id'])

def downgrade():
    op.drop_table('resource_metrics')
    op.drop_table('task_metrics')
    op.drop_table('project_metrics') 