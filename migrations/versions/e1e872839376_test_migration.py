"""test migration

Revision ID: e1e872839376
Revises: 062eaa6547b0
Create Date: 2026-07-24 16:26:54.642519

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1e872839376'
down_revision: Union[str, Sequence[str], None] = '062eaa6547b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
