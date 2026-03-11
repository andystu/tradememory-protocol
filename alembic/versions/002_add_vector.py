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
    # Use raw SQL since SQLAlchemy doesn't have native pgvector type
    op.execute(
        "ALTER TABLE episodic_memory ADD COLUMN IF NOT EXISTS embedding vector(384)"
    )


def downgrade() -> None:
    op.drop_column("episodic_memory", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
