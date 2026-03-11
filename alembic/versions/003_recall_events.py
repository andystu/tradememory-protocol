"""Add recall_events table (TimescaleDB hypertable).

Revision ID: 003
Revises: 002
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recall_events",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("query_symbol", sa.String(), nullable=True),
        sa.Column("query_regime", sa.String(), nullable=True),
        sa.Column("query_session", sa.String(), nullable=True),
        sa.Column("query_atr_d1", sa.Float(), nullable=True),
        sa.Column("memories_returned", sa.Integer(), nullable=True),
        sa.Column("avg_score", sa.Float(), nullable=True),
        sa.Column("avg_q", sa.Float(), nullable=True),
        sa.Column("avg_sim", sa.Float(), nullable=True),
        sa.Column("avg_rec", sa.Float(), nullable=True),
        sa.Column("avg_conf", sa.Float(), nullable=True),
        sa.Column("avg_aff", sa.Float(), nullable=True),
        sa.Column("negative_ratio", sa.Float(), nullable=True),
        sa.Column("query_context_json", JSONB(), nullable=True),
        # Composite PK: TimescaleDB requires partition column in PK
        sa.PrimaryKeyConstraint("id", "timestamp"),
    )

    # Convert to TimescaleDB hypertable for efficient time-series queries
    op.execute(
        "SELECT create_hypertable('recall_events', 'timestamp', if_not_exists => TRUE)"
    )


def downgrade() -> None:
    op.drop_table("recall_events")
