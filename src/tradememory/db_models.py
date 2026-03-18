"""
SQLAlchemy 2.0 ORM models for PostgreSQL.

Mirrors all 9 tables from db.py (SQLite) with proper PostgreSQL types:
- TEXT timestamps → TIMESTAMPTZ
- TEXT JSON → JSONB
- Model naming: XxxModel
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# ========== Core Tables ==========


class TradeRecordModel(Base):
    """Trade records — L1 raw trade data."""

    __tablename__ = "trade_records"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    lot_size: Mapped[float] = mapped_column(Float, nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    market_context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    trade_references: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)

    # Outcome (filled after trade closes)
    exit_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl_r: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hold_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    exit_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    slippage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    execution_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Reflection
    lessons: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=list)
    grade: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("idx_trade_timestamp", "timestamp"),
        Index("idx_trade_strategy", "strategy"),
    )


class SessionStateModel(Base):
    """Agent session state for cross-session persistence."""

    __tablename__ = "session_state"

    agent_id: Mapped[str] = mapped_column(String, primary_key=True)
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    warm_memory: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    active_positions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    risk_constraints: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


# ========== L2: Pattern Discovery ==========


class PatternModel(Base):
    """Discovered trading patterns — L2 layer."""

    __tablename__ = "patterns"

    pattern_id: Mapped[str] = mapped_column(String, primary_key=True)
    pattern_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    date_range: Mapped[str] = mapped_column(String, nullable=False)
    strategy: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    symbol: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(
        String, nullable=False, server_default="backtest_auto"
    )
    validation_status: Mapped[str] = mapped_column(
        String, nullable=False, server_default="IN_SAMPLE"
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    adjustments: Mapped[list["StrategyAdjustmentModel"]] = relationship(
        back_populates="source_pattern"
    )

    __table_args__ = (
        Index("idx_pattern_strategy_symbol", "strategy", "symbol"),
        Index("idx_pattern_type", "pattern_type"),
    )


# ========== L3: Strategy Adjustments ==========


class StrategyAdjustmentModel(Base):
    """Strategy parameter adjustments — L3 layer."""

    __tablename__ = "strategy_adjustments"

    adjustment_id: Mapped[str] = mapped_column(String, primary_key=True)
    adjustment_type: Mapped[str] = mapped_column(String, nullable=False)
    parameter: Mapped[str] = mapped_column(String, nullable=False)
    old_value: Mapped[str] = mapped_column(String, nullable=False)
    new_value: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source_pattern_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("patterns.pattern_id"), nullable=True
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default="proposed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    source_pattern: Mapped[Optional["PatternModel"]] = relationship(
        back_populates="adjustments"
    )

    __table_args__ = (
        Index("idx_adjustment_status", "status"),
        Index("idx_adjustment_type", "adjustment_type"),
    )


# ========== OWM Tables ==========


class EpisodicMemoryModel(Base):
    """Episodic memory — OWM Section 2.1."""

    __tablename__ = "episodic_memory"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    context_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    context_regime: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    context_volatility_regime: Mapped[Optional[str]] = mapped_column(
        String, nullable=True
    )
    context_session: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    context_atr_d1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    context_atr_h1: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    lot_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl_r: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    hold_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_adverse_excursion: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, default=0.5)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True, default=list)
    retrieval_strength: Mapped[Optional[float]] = mapped_column(Float, default=1.0)
    retrieval_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    last_retrieved: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_episodic_regime", "context_regime"),
        Index("idx_episodic_strategy", "strategy"),
        Index("idx_episodic_timestamp", "timestamp"),
        Index("idx_episodic_pnl_r", "pnl_r"),
    )


class SemanticMemoryModel(Base):
    """Semantic memory — OWM Section 2.2 (Bayesian beliefs)."""

    __tablename__ = "semantic_memory"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    proposition: Mapped[str] = mapped_column(Text, nullable=False)
    alpha: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
    beta: Mapped[float] = mapped_column(Float, nullable=False, server_default="1.0")
    sample_size: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    strategy: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    symbol: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    regime: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    volatility_regime: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    validity_conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_confirmed: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_contradicted: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source: Mapped[str] = mapped_column(String, nullable=False)
    retrieval_strength: Mapped[Optional[float]] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProceduralMemoryModel(Base):
    """Procedural memory — OWM Section 2.3 (behavioral learning)."""

    __tablename__ = "procedural_memory"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    behavior_type: Mapped[str] = mapped_column(String, nullable=False)
    sample_size: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    avg_hold_winners: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_hold_losers: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    disposition_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_lot_mean: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_lot_variance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    kelly_fraction_suggested: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    lot_vs_kelly_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AffectiveStateModel(Base):
    """Affective state — OWM Section 2.4 (emotional state)."""

    __tablename__ = "affective_state"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    confidence_level: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.5"
    )
    risk_appetite: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="1.0"
    )
    momentum_bias: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.0"
    )
    peak_equity: Mapped[float] = mapped_column(Float, nullable=False)
    current_equity: Mapped[float] = mapped_column(Float, nullable=False)
    drawdown_state: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.0"
    )
    max_acceptable_drawdown: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.20"
    )
    consecutive_wins: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    consecutive_losses: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    history_json: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=list
    )


class ProspectiveMemoryModel(Base):
    """Prospective memory — OWM Section 2.5 (future planning)."""

    __tablename__ = "prospective_memory"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    trigger_type: Mapped[str] = mapped_column(String, nullable=False)
    trigger_condition: Mapped[str] = mapped_column(Text, nullable=False)
    planned_action: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, server_default="active"
    )
    priority: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0.5"
    )
    expiry: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    source_episodic_ids: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    source_semantic_ids: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=list
    )
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    outcome_pnl_r: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    outcome_reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_prospective_status", "status"),
        Index("idx_prospective_trigger", "trigger_type"),
    )
