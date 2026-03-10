"""Add pgvector extension and embedding column to episodic_memory.

Revision ID: 002
Revises: 001
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # VECTOR(384) for sentence-transformers all-MiniLM-L6-v2 output dim
    op.add_column(
        "episodic_memory",
        sa.Column("embedding", sa.LargeBinary(), nullable=True, comment="VECTOR(384)"),
    )
    # Note: actual pgvector VECTOR type will be used via raw SQL
    # because SQLAlchemy doesn't have native pgvector type yet.
    op.execute(
        "ALTER TABLE episodic_memory ALTER COLUMN embedding TYPE vector(384) USING embedding::vector(384)"
    )


def downgrade() -> None:
    op.drop_column("episodic_memory", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
