"""Initial schema — 9 tables from SQLite migrated to PostgreSQL.

Revision ID: 001
Revises: (none)
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========== Core Tables ==========

    op.create_table(
        "trade_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("lot_size", sa.Float(), nullable=False),
        sa.Column("strategy", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("market_context", JSONB(), nullable=False, server_default="{}"),
        sa.Column("trade_references", JSONB(), nullable=False, server_default="[]"),
        sa.Column("exit_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("pnl", sa.Float(), nullable=True),
        sa.Column("pnl_r", sa.Float(), nullable=True),
        sa.Column("hold_duration", sa.Integer(), nullable=True),
        sa.Column("exit_reasoning", sa.Text(), nullable=True),
        sa.Column("slippage", sa.Float(), nullable=True),
        sa.Column("execution_quality", sa.Float(), nullable=True),
        sa.Column("lessons", sa.Text(), nullable=True),
        sa.Column("tags", JSONB(), nullable=True, server_default="[]"),
        sa.Column("grade", sa.String(), nullable=True),
    )
    op.create_index("idx_trade_timestamp", "trade_records", ["timestamp"])
    op.create_index("idx_trade_strategy", "trade_records", ["strategy"])

    op.create_table(
        "session_state",
        sa.Column("agent_id", sa.String(), primary_key=True),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=False),
        sa.Column("warm_memory", JSONB(), nullable=False, server_default="{}"),
        sa.Column("active_positions", JSONB(), nullable=False, server_default="[]"),
        sa.Column("risk_constraints", JSONB(), nullable=False, server_default="{}"),
    )

    # ========== L2: Pattern Discovery ==========

    op.create_table(
        "patterns",
        sa.Column("pattern_id", sa.String(), primary_key=True),
        sa.Column("pattern_type", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("date_range", sa.String(), nullable=False),
        sa.Column("strategy", sa.String(), nullable=True),
        sa.Column("symbol", sa.String(), nullable=True),
        sa.Column("metrics", JSONB(), nullable=False, server_default="{}"),
        sa.Column("source", sa.String(), nullable=False, server_default="backtest_auto"),
        sa.Column(
            "validation_status", sa.String(), nullable=False, server_default="IN_SAMPLE"
        ),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_pattern_strategy_symbol", "patterns", ["strategy", "symbol"])
    op.create_index("idx_pattern_type", "patterns", ["pattern_type"])

    # ========== L3: Strategy Adjustments ==========

    op.create_table(
        "strategy_adjustments",
        sa.Column("adjustment_id", sa.String(), primary_key=True),
        sa.Column("adjustment_type", sa.String(), nullable=False),
        sa.Column("parameter", sa.String(), nullable=False),
        sa.Column("old_value", sa.String(), nullable=False),
        sa.Column("new_value", sa.String(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "source_pattern_id",
            sa.String(),
            sa.ForeignKey("patterns.pattern_id"),
            nullable=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="proposed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_adjustment_status", "strategy_adjustments", ["status"])
    op.create_index("idx_adjustment_type", "strategy_adjustments", ["adjustment_type"])

    # ========== OWM Tables ==========

    op.create_table(
        "episodic_memory",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("context_json", JSONB(), nullable=False, server_default="{}"),
        sa.Column("context_regime", sa.String(), nullable=True),
        sa.Column("context_volatility_regime", sa.String(), nullable=True),
        sa.Column("context_session", sa.String(), nullable=True),
        sa.Column("context_atr_d1", sa.Float(), nullable=True),
        sa.Column("context_atr_h1", sa.Float(), nullable=True),
        sa.Column("strategy", sa.String(), nullable=False),
        sa.Column("direction", sa.String(), nullable=False),
        sa.Column("entry_price", sa.Float(), nullable=False),
        sa.Column("lot_size", sa.Float(), nullable=True),
        sa.Column("exit_price", sa.Float(), nullable=True),
        sa.Column("pnl", sa.Float(), nullable=True),
        sa.Column("pnl_r", sa.Float(), nullable=True),
        sa.Column("hold_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("max_adverse_excursion", sa.Float(), nullable=True),
        sa.Column("reflection", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), server_default="0.5"),
        sa.Column("tags", JSONB(), nullable=True, server_default="[]"),
        sa.Column("retrieval_strength", sa.Float(), server_default="1.0"),
        sa.Column("retrieval_count", sa.Integer(), server_default="0"),
        sa.Column("last_retrieved", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_episodic_regime", "episodic_memory", ["context_regime"])
    op.create_index("idx_episodic_strategy", "episodic_memory", ["strategy"])
    op.create_index("idx_episodic_timestamp", "episodic_memory", ["timestamp"])
    op.create_index("idx_episodic_pnl_r", "episodic_memory", ["pnl_r"])

    op.create_table(
        "semantic_memory",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("proposition", sa.Text(), nullable=False),
        sa.Column("alpha", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("beta", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("strategy", sa.String(), nullable=True),
        sa.Column("symbol", sa.String(), nullable=True),
        sa.Column("regime", sa.String(), nullable=True),
        sa.Column("volatility_regime", sa.String(), nullable=True),
        sa.Column("validity_conditions", sa.Text(), nullable=True),
        sa.Column("last_confirmed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_contradicted", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("retrieval_strength", sa.Float(), server_default="1.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "procedural_memory",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("strategy", sa.String(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("behavior_type", sa.String(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_hold_winners", sa.Float(), nullable=True),
        sa.Column("avg_hold_losers", sa.Float(), nullable=True),
        sa.Column("disposition_ratio", sa.Float(), nullable=True),
        sa.Column("actual_lot_mean", sa.Float(), nullable=True),
        sa.Column("actual_lot_variance", sa.Float(), nullable=True),
        sa.Column("kelly_fraction_suggested", sa.Float(), nullable=True),
        sa.Column("lot_vs_kelly_ratio", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "affective_state",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("confidence_level", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("risk_appetite", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("momentum_bias", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("peak_equity", sa.Float(), nullable=False),
        sa.Column("current_equity", sa.Float(), nullable=False),
        sa.Column("drawdown_state", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "max_acceptable_drawdown",
            sa.Float(),
            nullable=False,
            server_default="0.20",
        ),
        sa.Column("consecutive_wins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "consecutive_losses", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("last_updated", sa.DateTime(timezone=True), nullable=False),
        sa.Column("history_json", JSONB(), nullable=True, server_default="[]"),
    )

    op.create_table(
        "prospective_memory",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("trigger_type", sa.String(), nullable=False),
        sa.Column("trigger_condition", sa.Text(), nullable=False),
        sa.Column("planned_action", sa.Text(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("priority", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("expiry", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_episodic_ids", JSONB(), nullable=True, server_default="[]"),
        sa.Column("source_semantic_ids", JSONB(), nullable=True, server_default="[]"),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome_pnl_r", sa.Float(), nullable=True),
        sa.Column("outcome_reflection", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_prospective_status", "prospective_memory", ["status"])
    op.create_index("idx_prospective_trigger", "prospective_memory", ["trigger_type"])


def downgrade() -> None:
    op.drop_table("prospective_memory")
    op.drop_table("affective_state")
    op.drop_table("procedural_memory")
    op.drop_table("semantic_memory")
    op.drop_table("episodic_memory")
    op.drop_table("strategy_adjustments")
    op.drop_table("patterns")
    op.drop_table("session_state")
    op.drop_table("trade_records")
