"""improve offer constraints

Revision ID: f26b7869f3ea
Revises: e1e872839376
Create Date: 2026-07-24 16:31:36.110227
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f26b7869f3ea"
down_revision: Union[str, Sequence[str], None] = "e1e872839376"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add constraints, indexes and database defaults to offer."""

    op.create_unique_constraint(
        "uq_offer_source_external_id",
        "offer",
        ["source", "external_id"],
    )

    op.drop_constraint(
        "offer_dealer_id_fkey",
        "offer",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "fk_offer_dealer_id_dealer",
        "offer",
        "dealer",
        ["dealer_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_offer_is_active",
        "offer",
        ["is_active"],
        unique=False,
    )

    op.create_index(
        "ix_offer_last_seen_at",
        "offer",
        ["last_seen_at"],
        unique=False,
    )

    op.alter_column(
        "offer",
        "currency",
        existing_type=sa.String(length=3),
        existing_nullable=False,
        server_default=sa.text("'EUR'"),
    )

    op.alter_column(
        "offer",
        "is_active",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        server_default=sa.true(),
    )

    op.alter_column(
        "offer",
        "first_seen_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=sa.func.now(),
    )

    op.alter_column(
        "offer",
        "last_seen_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=sa.func.now(),
    )

    op.alter_column(
        "offer",
        "created_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=sa.func.now(),
    )

    op.alter_column(
        "offer",
        "updated_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=sa.func.now(),
    )


def downgrade() -> None:
    """Remove offer constraints, indexes and database defaults."""

    op.alter_column(
        "offer",
        "updated_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=None,
    )

    op.alter_column(
        "offer",
        "created_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=None,
    )

    op.alter_column(
        "offer",
        "last_seen_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=None,
    )

    op.alter_column(
        "offer",
        "first_seen_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=None,
    )

    op.alter_column(
        "offer",
        "is_active",
        existing_type=sa.Boolean(),
        existing_nullable=False,
        server_default=None,
    )

    op.alter_column(
        "offer",
        "currency",
        existing_type=sa.String(length=3),
        existing_nullable=False,
        server_default=None,
    )

    op.drop_index(
        "ix_offer_last_seen_at",
        table_name="offer",
    )

    op.drop_index(
        "ix_offer_is_active",
        table_name="offer",
    )

    op.drop_constraint(
        "fk_offer_dealer_id_dealer",
        "offer",
        type_="foreignkey",
    )

    op.create_foreign_key(
        "offer_dealer_id_fkey",
        "offer",
        "dealer",
        ["dealer_id"],
        ["id"],
    )

    op.drop_constraint(
        "uq_offer_source_external_id",
        "offer",
        type_="unique",
    )