"""add vehicle configuration tables

Revision ID: 8d9a3c4b5e6f
Revises: f13f6b3a9c21
Create Date: 2026-07-27 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "8d9a3c4b5e6f"
down_revision: Union[str, Sequence[str], None] = "f13f6b3a9c21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vehicle_configuration",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("configuration_id", sa.String(length=64), nullable=True),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("resolved_url", sa.Text(), nullable=True),
        sa.Column("resolved_url_hash", sa.String(length=64), nullable=False),
        sa.Column("brand", sa.String(length=32), nullable=False),
        sa.Column("series_code", sa.String(length=16), nullable=True),
        sa.Column("model_code", sa.String(length=16), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("variant", sa.String(length=120), nullable=True),
        sa.Column("body", sa.String(length=120), nullable=True),
        sa.Column("paint_code", sa.String(length=32), nullable=True),
        sa.Column("paint_name", sa.String(length=255), nullable=True),
        sa.Column("upholstery_code", sa.String(length=32), nullable=True),
        sa.Column("upholstery_name", sa.String(length=255), nullable=True),
        sa.Column("list_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="EUR"),
        sa.Column("effect_date", sa.Date(), nullable=True),
        sa.Column("parse_status", sa.String(length=32), nullable=False),
        sa.Column("parser_version", sa.String(length=32), nullable=False),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("normalized_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "configuration_id", "effect_date", name="uq_vehicle_configuration_provider_id_date"),
        sa.UniqueConstraint("provider", "resolved_url_hash", name="uq_vehicle_configuration_provider_hash"),
    )
    op.create_index(op.f("ix_vehicle_configuration_configuration_id"), "vehicle_configuration", ["configuration_id"], unique=False)
    op.create_index(op.f("ix_vehicle_configuration_parse_status"), "vehicle_configuration", ["parse_status"], unique=False)
    op.create_index(op.f("ix_vehicle_configuration_resolved_url_hash"), "vehicle_configuration", ["resolved_url_hash"], unique=False)

    op.create_table(
        "vehicle_configuration_feature",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("configuration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_code", sa.String(length=32), nullable=True),
        sa.Column("feature_key", sa.String(length=120), nullable=False),
        sa.Column("feature_value", sa.Text(), nullable=False),
        sa.Column("display_label", sa.String(length=200), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("is_standard", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["configuration_id"], ["vehicle_configuration.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "configuration_id",
            "feature_key",
            "feature_code",
            "sort_order",
            name="uq_vehicle_configuration_feature",
        ),
    )
    op.create_index(op.f("ix_vehicle_configuration_feature_configuration_id"), "vehicle_configuration_feature", ["configuration_id"], unique=False)

    op.add_column("campaign_configuration", sa.Column("vehicle_configuration_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f("ix_campaign_configuration_vehicle_configuration_id"), "campaign_configuration", ["vehicle_configuration_id"], unique=False)
    op.create_foreign_key(
        "fk_campaign_configuration_vehicle_configuration",
        "campaign_configuration",
        "vehicle_configuration",
        ["vehicle_configuration_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_campaign_configuration_vehicle_configuration", "campaign_configuration", type_="foreignkey")
    op.drop_index(op.f("ix_campaign_configuration_vehicle_configuration_id"), table_name="campaign_configuration")
    op.drop_column("campaign_configuration", "vehicle_configuration_id")

    op.drop_index(op.f("ix_vehicle_configuration_feature_configuration_id"), table_name="vehicle_configuration_feature")
    op.drop_table("vehicle_configuration_feature")

    op.drop_index(op.f("ix_vehicle_configuration_resolved_url_hash"), table_name="vehicle_configuration")
    op.drop_index(op.f("ix_vehicle_configuration_parse_status"), table_name="vehicle_configuration")
    op.drop_index(op.f("ix_vehicle_configuration_configuration_id"), table_name="vehicle_configuration")
    op.drop_table("vehicle_configuration")
