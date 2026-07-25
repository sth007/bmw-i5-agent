"""add campaign dispatch lifecycle fields

Revision ID: f13f6b3a9c21
Revises: c8b7d7a1f4aa
Create Date: 2026-07-25 12:55:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f13f6b3a9c21"
down_revision: Union[str, Sequence[str], None] = "c8b7d7a1f4aa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaign", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("campaign", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("campaign", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("campaign", sa.Column("completed_by", sa.String(length=120), nullable=True))
    op.add_column("campaign", sa.Column("completion_execution_id", sa.String(length=120), nullable=True))
    op.create_index(op.f("ix_campaign_started_at"), "campaign", ["started_at"], unique=False)
    op.create_index(op.f("ix_campaign_completed_at"), "campaign", ["completed_at"], unique=False)

    op.execute(
        """
        UPDATE campaign
        SET status = CASE UPPER(status)
            WHEN 'ACTIVE' THEN 'STARTED'
            WHEN 'PAUSED' THEN 'STARTED'
            WHEN 'COMPLETED' THEN 'COMPLETED'
            WHEN 'CANCELLED' THEN 'CANCELLED'
            ELSE 'DRAFT'
        END
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_completed_at"), table_name="campaign")
    op.drop_index(op.f("ix_campaign_started_at"), table_name="campaign")
    op.drop_column("campaign", "completion_execution_id")
    op.drop_column("campaign", "completed_by")
    op.drop_column("campaign", "cancelled_at")
    op.drop_column("campaign", "completed_at")
    op.drop_column("campaign", "started_at")
