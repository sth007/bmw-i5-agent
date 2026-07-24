"""create campaign offer tables and drop price history

Revision ID: 9c3f7a4b7d21
Revises: 4f1e140dbedd
Create Date: 2026-07-24 20:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "9c3f7a4b7d21"
down_revision: Union[str, Sequence[str], None] = "4f1e140dbedd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "campaign",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cheapest_exact_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("cheapest_alternative_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("cheapest_overall_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_campaign_status"), "campaign", ["status"], unique=False)

    op.create_table(
        "campaign_configuration",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("configuration_url", sa.Text(), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("variant", sa.String(length=120), nullable=False),
        sa.Column("package", sa.String(length=120), nullable=True),
        sa.Column("list_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("maximum_target_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payment_preference", sa.String(length=16), server_default="either", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id"),
    )

    op.create_table(
        "configuration_requirement",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("configuration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_key", sa.String(length=120), nullable=False),
        sa.Column("feature_value", sa.Text(), nullable=True),
        sa.Column("normalized_key", sa.String(length=120), nullable=False),
        sa.Column("normalized_value", sa.String(length=200), nullable=True),
        sa.Column("display_label", sa.String(length=200), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["configuration_id"], ["campaign_configuration.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_configuration_requirement_configuration_id"),
        "configuration_requirement",
        ["configuration_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_configuration_requirement_normalized_key"),
        "configuration_requirement",
        ["normalized_key"],
        unique=False,
    )

    op.create_table(
        "dealer_offer",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dealer_name", sa.String(length=200), nullable=False),
        sa.Column("dealer_reference", sa.String(length=120), nullable=True),
        sa.Column("source_type", sa.String(length=24), server_default="manual", nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="EUR", nullable=False),
        sa.Column("vehicle_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("transfer_cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("registration_cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("total_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("cash_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("financing_required", sa.Boolean(), nullable=True),
        sa.Column("financing_total_cost", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column("production_date", sa.Date(), nullable=True),
        sa.Column("model_year", sa.Integer(), nullable=True),
        sa.Column("holding_period_months", sa.Integer(), nullable=True),
        sa.Column("day_registration", sa.Boolean(), nullable=True),
        sa.Column("trade_in_required", sa.Boolean(), nullable=True),
        sa.Column("offer_valid_until", sa.Date(), nullable=True),
        sa.Column("raw_response", sa.Text(), nullable=False),
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dealer_offer_campaign_id"), "dealer_offer", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_dealer_offer_total_price"), "dealer_offer", ["total_price"], unique=False)

    op.create_table(
        "dealer_offer_feature",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("offer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_key", sa.String(length=120), nullable=False),
        sa.Column("feature_value", sa.Text(), nullable=True),
        sa.Column("normalized_key", sa.String(length=120), nullable=False),
        sa.Column("normalized_value", sa.String(length=200), nullable=True),
        sa.Column("display_label", sa.String(length=200), nullable=True),
        sa.Column("is_available", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["offer_id"], ["dealer_offer.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_dealer_offer_feature_offer_id"), "dealer_offer_feature", ["offer_id"], unique=False)
    op.create_index(
        op.f("ix_dealer_offer_feature_normalized_key"),
        "dealer_offer_feature",
        ["normalized_key"],
        unique=False,
    )

    op.drop_index(op.f("ix_price_history_offer_id"), table_name="price_history")
    op.drop_index(op.f("ix_price_history_observed_at"), table_name="price_history")
    op.drop_table("price_history")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("offer_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="EUR", nullable=False),
        sa.Column("observed_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["offer.id"],
            name="fk_price_history_offer_id_offer",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_price_history_observed_at"), "price_history", ["observed_at"], unique=False)
    op.create_index(op.f("ix_price_history_offer_id"), "price_history", ["offer_id"], unique=False)

    op.drop_index(op.f("ix_dealer_offer_feature_normalized_key"), table_name="dealer_offer_feature")
    op.drop_index(op.f("ix_dealer_offer_feature_offer_id"), table_name="dealer_offer_feature")
    op.drop_table("dealer_offer_feature")

    op.drop_index(op.f("ix_dealer_offer_total_price"), table_name="dealer_offer")
    op.drop_index(op.f("ix_dealer_offer_campaign_id"), table_name="dealer_offer")
    op.drop_table("dealer_offer")

    op.drop_index(op.f("ix_configuration_requirement_normalized_key"), table_name="configuration_requirement")
    op.drop_index(op.f("ix_configuration_requirement_configuration_id"), table_name="configuration_requirement")
    op.drop_table("configuration_requirement")

    op.drop_table("campaign_configuration")

    op.drop_index(op.f("ix_campaign_status"), table_name="campaign")
    op.drop_table("campaign")
