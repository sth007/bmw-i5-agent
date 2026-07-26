"""add inbound extraction fields and dealer-offer uniqueness

Revision ID: 6d5c9e4f8a12
Revises: f13f6b3a9c21, f26b7869f3ea
Create Date: 2026-07-26 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6d5c9e4f8a12"
down_revision: Union[str, Sequence[str], None] = ("f13f6b3a9c21", "f26b7869f3ea")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inbound_email", sa.Column("message_type", sa.String(length=64), nullable=True))
    op.add_column("inbound_email", sa.Column("extraction_confidence", sa.Numeric(precision=5, scale=4), nullable=True))
    op.add_column("inbound_email", sa.Column("extraction_reason", sa.Text(), nullable=True))
    op.add_column("inbound_email", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE inbound_email SET processing_status = 'REGISTERED' WHERE processing_status = 'RECEIVED'")
    op.execute(
        """
        DELETE FROM dealer_offer older
        USING dealer_offer newer
        WHERE older.inbound_email_id IS NOT NULL
          AND newer.inbound_email_id = older.inbound_email_id
          AND (
            newer.updated_at > older.updated_at OR
            (newer.updated_at = older.updated_at AND newer.created_at > older.created_at) OR
            (newer.updated_at = older.updated_at AND newer.created_at = older.created_at AND newer.id > older.id)
          )
        """
    )

    op.create_unique_constraint(
        "uq_dealer_offer_inbound_email_id",
        "dealer_offer",
        ["inbound_email_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_dealer_offer_inbound_email_id", "dealer_offer", type_="unique")
    op.drop_column("inbound_email", "processed_at")
    op.drop_column("inbound_email", "extraction_reason")
    op.drop_column("inbound_email", "extraction_confidence")
    op.drop_column("inbound_email", "message_type")
