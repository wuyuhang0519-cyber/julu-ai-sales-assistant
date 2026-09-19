"""bonus features: quotes, proposals, multichannel and CRM sync"""
revision="0003";down_revision="0002";branch_labels=None;depends_on=None
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table("quotes",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("lead_id",sa.Integer(),sa.ForeignKey("leads.id"),nullable=False),
        sa.Column("quote_number",sa.String(60),nullable=False,unique=True),
        sa.Column("package_code",sa.String(40),nullable=False),
        sa.Column("currency",sa.String(10),nullable=False),
        sa.Column("subtotal",sa.Integer(),nullable=False),
        sa.Column("discount_percent",sa.Integer(),nullable=False),
        sa.Column("total",sa.Integer(),nullable=False),
        sa.Column("line_items",sa.JSON(),nullable=False),
        sa.Column("assumptions",sa.JSON(),nullable=False),
        sa.Column("status",sa.String(30),nullable=False),
        sa.Column("valid_until",sa.DateTime(timezone=True),nullable=False),
        sa.Column("approved_at",sa.DateTime(timezone=True)),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_quotes_lead_id","quotes",["lead_id"])
    op.create_index("ix_quotes_quote_number","quotes",["quote_number"],unique=True)
    op.create_table("proposals",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("lead_id",sa.Integer(),sa.ForeignKey("leads.id"),nullable=False),
        sa.Column("quote_id",sa.Integer(),sa.ForeignKey("quotes.id")),
        sa.Column("proposal_number",sa.String(60),nullable=False,unique=True),
        sa.Column("language",sa.String(10),nullable=False),
        sa.Column("title",sa.String(240),nullable=False),
        sa.Column("content_markdown",sa.Text(),nullable=False),
        sa.Column("knowledge_refs",sa.JSON(),nullable=False),
        sa.Column("status",sa.String(30),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_proposals_lead_id","proposals",["lead_id"])
    op.create_index("ix_proposals_proposal_number","proposals",["proposal_number"],unique=True)
    op.create_table("channel_deliveries",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("lead_id",sa.Integer(),sa.ForeignKey("leads.id")),
        sa.Column("channel",sa.String(30),nullable=False),
        sa.Column("recipient_redacted",sa.String(220),nullable=False),
        sa.Column("provider",sa.String(40),nullable=False),
        sa.Column("provider_message_id",sa.String(255)),
        sa.Column("status",sa.String(30),nullable=False),
        sa.Column("error_type",sa.String(80)),
        sa.Column("content_summary",sa.Text(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_channel_deliveries_lead_id","channel_deliveries",["lead_id"])
    op.create_table("crm_syncs",
        sa.Column("id",sa.Integer(),primary_key=True),
        sa.Column("lead_id",sa.Integer(),sa.ForeignKey("leads.id"),nullable=False),
        sa.Column("provider",sa.String(30),nullable=False),
        sa.Column("operation",sa.String(40),nullable=False),
        sa.Column("status",sa.String(30),nullable=False),
        sa.Column("external_id",sa.String(255)),
        sa.Column("error_type",sa.String(80)),
        sa.Column("detail",sa.JSON(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False))
    op.create_index("ix_crm_syncs_lead_id","crm_syncs",["lead_id"])

def downgrade():
    op.drop_table("crm_syncs")
    op.drop_table("channel_deliveries")
    op.drop_table("proposals")
    op.drop_table("quotes")