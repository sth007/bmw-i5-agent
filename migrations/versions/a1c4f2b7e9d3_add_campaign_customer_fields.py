"""add campaign customer fields

Revision ID: a1c4f2b7e9d3
Revises: 6d5c9e4f8a12
Create Date: 2026-07-26 14:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1c4f2b7e9d3"
down_revision: Union[str, Sequence[str], None] = "6d5c9e4f8a12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaign", sa.Column("customer_name", sa.String(length=200), nullable=True))
    op.add_column("campaign", sa.Column("customer_email", sa.String(length=320), nullable=True))
    op.add_column("campaign", sa.Column("customer_phone", sa.String(length=80), nullable=True))


def downgrade() -> None:
    op.drop_column("campaign", "customer_phone")
    op.drop_column("campaign", "customer_email")
    op.drop_column("campaign", "customer_name")
