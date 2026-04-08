"""framework_outbox

Revision ID: framework_outbox
Revises:
Create Date: 2026-04-08 00:00:00

"""

from alembic import op  # pyright: ignore[reportMissingImports]
import sqlalchemy as sa


revision = "framework_outbox"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("event_data", sa.Text(), nullable=False),
        sa.Column("aggregate_id", sa.String(length=36), nullable=False),
        sa.Column("aggregate_type", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("event_id", name="pk_outbox_events"),
    )
    op.create_index("idx_outbox_aggregate", "outbox_events", ["aggregate_type", "aggregate_id"], unique=False)
    op.create_index("idx_outbox_aggregate_id", "outbox_events", ["aggregate_id"], unique=False)
    op.create_index("idx_outbox_event_type", "outbox_events", ["event_type"], unique=False)
    op.create_index("idx_outbox_status", "outbox_events", ["status"], unique=False)
    op.create_index("idx_outbox_status_created", "outbox_events", ["status", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_outbox_status_created", table_name="outbox_events")
    op.drop_index("idx_outbox_status", table_name="outbox_events")
    op.drop_index("idx_outbox_event_type", table_name="outbox_events")
    op.drop_index("idx_outbox_aggregate_id", table_name="outbox_events")
    op.drop_index("idx_outbox_aggregate", table_name="outbox_events")
    op.drop_table("outbox_events")
