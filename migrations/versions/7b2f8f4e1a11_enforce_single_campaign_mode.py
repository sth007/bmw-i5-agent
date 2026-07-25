"""enforce single campaign mode

Revision ID: 7b2f8f4e1a11
Revises: f13f6b3a9c21
Create Date: 2026-07-25 20:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7b2f8f4e1a11"
down_revision: Union[str, Sequence[str], None] = "f13f6b3a9c21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaign", sa.Column("singleton_key", sa.SmallInteger(), nullable=True, server_default="1"))

    bind = op.get_bind()

    keep_campaign_id = bind.execute(
        sa.text(
            """
            SELECT id
            FROM campaign
            ORDER BY
                CASE
                    WHEN status = 'STARTED' THEN 0
                    WHEN status = 'COMPLETED' THEN 1
                    ELSE 2
                END,
                started_at DESC NULLS LAST,
                created_at DESC NULLS LAST,
                id DESC
            LIMIT 1
            """
        )
    ).scalar()

    if keep_campaign_id is not None:
        bind.execute(
            sa.text(
                """
                DELETE FROM dealer_offer_feature
                WHERE offer_id IN (
                    SELECT id
                    FROM dealer_offer
                    WHERE campaign_id <> :keep_campaign_id
                )
                """
            ),
            {"keep_campaign_id": keep_campaign_id},
        )
        bind.execute(
            sa.text("DELETE FROM dealer_offer WHERE campaign_id <> :keep_campaign_id"),
            {"keep_campaign_id": keep_campaign_id},
        )
        bind.execute(
            sa.text("DELETE FROM inbound_email WHERE campaign_id <> :keep_campaign_id"),
            {"keep_campaign_id": keep_campaign_id},
        )
        bind.execute(
            sa.text(
                """
                DELETE FROM configuration_requirement
                WHERE configuration_id IN (
                    SELECT id
                    FROM campaign_configuration
                    WHERE campaign_id <> :keep_campaign_id
                )
                """
            ),
            {"keep_campaign_id": keep_campaign_id},
        )
        bind.execute(
            sa.text("DELETE FROM campaign_configuration WHERE campaign_id <> :keep_campaign_id"),
            {"keep_campaign_id": keep_campaign_id},
        )
        bind.execute(
            sa.text("DELETE FROM campaign_dealer_contact WHERE campaign_id <> :keep_campaign_id"),
            {"keep_campaign_id": keep_campaign_id},
        )
        bind.execute(
            sa.text("DELETE FROM campaign WHERE id <> :keep_campaign_id"),
            {"keep_campaign_id": keep_campaign_id},
        )

    bind.execute(sa.text("UPDATE campaign SET singleton_key = 1"))

    op.alter_column("campaign", "singleton_key", existing_type=sa.SmallInteger(), nullable=False, server_default="1")
    op.create_unique_constraint("uq_campaign_singleton", "campaign", ["singleton_key"])
    op.create_check_constraint("ck_campaign_singleton_key", "campaign", "singleton_key = 1")


def downgrade() -> None:
    op.drop_constraint("ck_campaign_singleton_key", "campaign", type_="check")
    op.drop_constraint("uq_campaign_singleton", "campaign", type_="unique")
    op.drop_column("campaign", "singleton_key")
