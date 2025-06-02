"""add sample success patterns

Revision ID: add_sample_success_patterns
Revises: create_success_patterns_table
Create Date: 2025-06-01 02:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = 'add_sample_success_patterns'
down_revision: Union[str, None] = 'create_success_patterns_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Insert sample success patterns
    op.execute("""
        INSERT INTO success_patterns (pattern_type, pattern_data, confidence_score, occurrence_count, impact_score)
        VALUES 
        (
            'team_composition',
            '{"pattern": "Cross-functional teams", "details": {"roles": ["frontend", "backend", "qa"], "min_experience": 2}, "benefits": ["Faster delivery", "Better quality", "Reduced dependencies"]}',
            0.85,
            12,
            0.9
        ),
        (
            'task_planning',
            '{"pattern": "Sprint planning best practices", "details": {"practices": ["Story point estimation", "Task breakdown", "Risk assessment"], "timeline": "2-week sprints"}, "benefits": ["Improved predictability", "Better resource allocation"]}',
            0.78,
            15,
            0.85
        ),
        (
            'execution',
            '{"pattern": "Code review process", "details": {"steps": ["Automated checks", "Peer review", "Lead review"], "timing": "Within 24 hours"}, "benefits": ["Higher code quality", "Knowledge sharing"]}',
            0.92,
            20,
            0.88
        ),
        (
            'collaboration',
            '{"pattern": "Daily standups", "details": {"format": "15-min updates", "focus": ["Blockers", "Progress", "Plans"], "timing": "Same time daily"}, "benefits": ["Early issue detection", "Team alignment"]}',
            0.95,
            25,
            0.87
        )
    """)


def downgrade() -> None:
    # Remove sample success patterns
    op.execute("DELETE FROM success_patterns") 