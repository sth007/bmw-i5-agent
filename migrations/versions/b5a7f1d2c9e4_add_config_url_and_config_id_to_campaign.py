"""add config_url and config_id to campaign

Revision ID: b5a7f1d2c9e4
Revises: 9c3f7a4b7d21
Create Date: 2026-07-24 22:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b5a7f1d2c9e4"
down_revision: Union[str, Sequence[str], None] = "9c3f7a4b7d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaign", sa.Column("config_url", sa.Text(), nullable=True))
    op.add_column("campaign", sa.Column("config_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_campaign_config_id"), "campaign", ["config_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_campaign_config_id"), table_name="campaign")
    op.drop_column("campaign", "config_id")
    op.drop_column("campaign", "config_url")
