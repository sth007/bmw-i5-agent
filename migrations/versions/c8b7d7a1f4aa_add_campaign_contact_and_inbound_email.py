"""add campaign contact and inbound email support

Revision ID: c8b7d7a1f4aa
Revises: b5a7f1d2c9e4
Create Date: 2026-07-24 23:55:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c8b7d7a1f4aa"
down_revision: Union[str, Sequence[str], None] = "b5a7f1d2c9e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_dealer_contact",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dealer_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reservation_owner", sa.String(length=120), nullable=True),
        sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("recipient_email", sa.String(length=255), nullable=True),
        sa.Column("original_subject", sa.Text(), nullable=True),
        sa.Column("rendered_body", sa.Text(), nullable=True),
        sa.Column("outbound_message_key", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("provider_thread_id", sa.String(length=255), nullable=True),
        sa.Column("internet_message_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dealer_id"], ["dealer.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "dealer_id", name="uq_campaign_dealer_contact_campaign_dealer"),
        sa.UniqueConstraint("outbound_message_key", name="uq_campaign_dealer_contact_outbound_message_key"),
    )
    op.create_index(op.f("ix_campaign_dealer_contact_campaign_id"), "campaign_dealer_contact", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_campaign_dealer_contact_dealer_id"), "campaign_dealer_contact", ["dealer_id"], unique=False)
    op.create_index(op.f("ix_campaign_dealer_contact_internet_message_id"), "campaign_dealer_contact", ["internet_message_id"], unique=False)
    op.create_index(op.f("ix_campaign_dealer_contact_provider_message_id"), "campaign_dealer_contact", ["provider_message_id"], unique=False)
    op.create_index(op.f("ix_campaign_dealer_contact_provider_thread_id"), "campaign_dealer_contact", ["provider_thread_id"], unique=False)
    op.create_index(op.f("ix_campaign_dealer_contact_status"), "campaign_dealer_contact", ["status"], unique=False)

    op.create_table(
        "inbound_email",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("dealer_id", sa.Integer(), nullable=True),
        sa.Column("campaign_dealer_contact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mailbox_address", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=False),
        sa.Column("provider_thread_id", sa.String(length=255), nullable=True),
        sa.Column("internet_message_id", sa.String(length=255), nullable=True),
        sa.Column("in_reply_to", sa.String(length=255), nullable=True),
        sa.Column("references", sa.Text(), nullable=True),
        sa.Column("sender_email", sa.String(length=255), nullable=True),
        sa.Column("sender_name", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("text_body", sa.Text(), nullable=True),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processing_status", sa.String(length=32), nullable=False),
        sa.Column("matching_status", sa.String(length=32), nullable=False),
        sa.Column("raw_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["campaign_dealer_contact_id"], ["campaign_dealer_contact.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dealer_id"], ["dealer.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_message_id", name="uq_inbound_email_provider_message"),
    )
    op.create_index(op.f("ix_inbound_email_campaign_dealer_contact_id"), "inbound_email", ["campaign_dealer_contact_id"], unique=False)
    op.create_index(op.f("ix_inbound_email_campaign_id"), "inbound_email", ["campaign_id"], unique=False)
    op.create_index(op.f("ix_inbound_email_dealer_id"), "inbound_email", ["dealer_id"], unique=False)
    op.create_index(op.f("ix_inbound_email_internet_message_id"), "inbound_email", ["internet_message_id"], unique=False)
    op.create_index(op.f("ix_inbound_email_matching_status"), "inbound_email", ["matching_status"], unique=False)
    op.create_index(op.f("ix_inbound_email_processing_status"), "inbound_email", ["processing_status"], unique=False)
    op.create_index(op.f("ix_inbound_email_provider_thread_id"), "inbound_email", ["provider_thread_id"], unique=False)
    op.create_index(op.f("ix_inbound_email_received_at"), "inbound_email", ["received_at"], unique=False)
    op.create_index(op.f("ix_inbound_email_sender_email"), "inbound_email", ["sender_email"], unique=False)

    op.add_column("dealer_offer", sa.Column("dealer_id", sa.Integer(), nullable=True))
    op.add_column("dealer_offer", sa.Column("inbound_email_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("dealer_offer", sa.Column("gross_final_price", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("dealer_offer", sa.Column("net_price", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("dealer_offer", sa.Column("list_price", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("dealer_offer", sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("dealer_offer", sa.Column("discount_percent", sa.Numeric(precision=7, scale=4), nullable=True))
    op.add_column("dealer_offer", sa.Column("delivery_cost", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("dealer_offer", sa.Column("other_costs", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("dealer_offer", sa.Column("delivery_time_text", sa.Text(), nullable=True))
    op.add_column("dealer_offer", sa.Column("valid_until", sa.Date(), nullable=True))
    op.add_column("dealer_offer", sa.Column("price_confidence", sa.Numeric(precision=5, scale=4), nullable=True))
    op.add_column("dealer_offer", sa.Column("extraction_status", sa.String(length=32), server_default="PARTIAL", nullable=False))
    op.add_column("dealer_offer", sa.Column("missing_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("dealer_offer", sa.Column("extraction_notes", sa.Text(), nullable=True))
    op.add_column("dealer_offer", sa.Column("raw_extraction", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index(op.f("ix_dealer_offer_dealer_id"), "dealer_offer", ["dealer_id"], unique=False)
    op.create_index(op.f("ix_dealer_offer_extraction_status"), "dealer_offer", ["extraction_status"], unique=False)
    op.create_index(op.f("ix_dealer_offer_gross_final_price"), "dealer_offer", ["gross_final_price"], unique=False)
    op.create_index(op.f("ix_dealer_offer_inbound_email_id"), "dealer_offer", ["inbound_email_id"], unique=False)
    op.create_foreign_key("fk_dealer_offer_dealer_id_dealer", "dealer_offer", "dealer", ["dealer_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_dealer_offer_inbound_email_id", "dealer_offer", "inbound_email", ["inbound_email_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_dealer_offer_inbound_email_id", "dealer_offer", type_="foreignkey")
    op.drop_constraint("fk_dealer_offer_dealer_id_dealer", "dealer_offer", type_="foreignkey")
    op.drop_index(op.f("ix_dealer_offer_inbound_email_id"), table_name="dealer_offer")
    op.drop_index(op.f("ix_dealer_offer_gross_final_price"), table_name="dealer_offer")
    op.drop_index(op.f("ix_dealer_offer_extraction_status"), table_name="dealer_offer")
    op.drop_index(op.f("ix_dealer_offer_dealer_id"), table_name="dealer_offer")
    op.drop_column("dealer_offer", "raw_extraction")
    op.drop_column("dealer_offer", "extraction_notes")
    op.drop_column("dealer_offer", "missing_fields")
    op.drop_column("dealer_offer", "extraction_status")
    op.drop_column("dealer_offer", "price_confidence")
    op.drop_column("dealer_offer", "valid_until")
    op.drop_column("dealer_offer", "delivery_time_text")
    op.drop_column("dealer_offer", "other_costs")
    op.drop_column("dealer_offer", "delivery_cost")
    op.drop_column("dealer_offer", "discount_percent")
    op.drop_column("dealer_offer", "discount_amount")
    op.drop_column("dealer_offer", "list_price")
    op.drop_column("dealer_offer", "net_price")
    op.drop_column("dealer_offer", "gross_final_price")
    op.drop_column("dealer_offer", "inbound_email_id")
    op.drop_column("dealer_offer", "dealer_id")

    op.drop_index(op.f("ix_inbound_email_sender_email"), table_name="inbound_email")
    op.drop_index(op.f("ix_inbound_email_received_at"), table_name="inbound_email")
    op.drop_index(op.f("ix_inbound_email_provider_thread_id"), table_name="inbound_email")
    op.drop_index(op.f("ix_inbound_email_processing_status"), table_name="inbound_email")
    op.drop_index(op.f("ix_inbound_email_matching_status"), table_name="inbound_email")
    op.drop_index(op.f("ix_inbound_email_internet_message_id"), table_name="inbound_email")
    op.drop_index(op.f("ix_inbound_email_dealer_id"), table_name="inbound_email")
    op.drop_index(op.f("ix_inbound_email_campaign_id"), table_name="inbound_email")
    op.drop_index(op.f("ix_inbound_email_campaign_dealer_contact_id"), table_name="inbound_email")
    op.drop_table("inbound_email")

    op.drop_index(op.f("ix_campaign_dealer_contact_status"), table_name="campaign_dealer_contact")
    op.drop_index(op.f("ix_campaign_dealer_contact_provider_thread_id"), table_name="campaign_dealer_contact")
    op.drop_index(op.f("ix_campaign_dealer_contact_provider_message_id"), table_name="campaign_dealer_contact")
    op.drop_index(op.f("ix_campaign_dealer_contact_internet_message_id"), table_name="campaign_dealer_contact")
    op.drop_index(op.f("ix_campaign_dealer_contact_dealer_id"), table_name="campaign_dealer_contact")
    op.drop_index(op.f("ix_campaign_dealer_contact_campaign_id"), table_name="campaign_dealer_contact")
    op.drop_table("campaign_dealer_contact")
