"""add campaign resolved configuration

Revision ID: 1a2b3c4d5e6f
Revises: d4e5f6a7b8c9
Create Date: 2026-07-28 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "1a2b3c4d5e6f"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaign_configuration",
        sa.Column("resolved_configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("campaign_configuration", "resolved_configuration")
