"""Tests for replay models — strategy normalization validator."""

import pytest
from tradememory.replay.models import (
    VALID_STRATEGIES,
    AgentDecision,
    DecisionType,
)


def _make_decision(**kwargs) -> AgentDecision:
    """Helper to build AgentDecision with required fields."""
    defaults = {
        "market_observation": "test",
        "reasoning_trace": "test",
        "decision": DecisionType.HOLD,
        "confidence": 0.5,
    }
    defaults.update(kwargs)
    return AgentDecision(**defaults)


class TestValidStrategies:
    def test_valid_strategies_list(self):
        assert VALID_STRATEGIES == [
            "VolBreakout",
            "IntradayMomentum",
            "PullbackEntry",
            "NONE",
        ]


class TestStrategyNormalization:
    """Validator maps LLM variations to canonical names."""

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            # Canonical names pass through
            ("VolBreakout", "VolBreakout"),
            ("IntradayMomentum", "IntradayMomentum"),
            ("PullbackEntry", "PullbackEntry"),
            ("NONE", "NONE"),
            # Common abbreviations
            ("VB", "VolBreakout"),
            ("IM", "IntradayMomentum"),
            ("PB", "PullbackEntry"),
            # Lowercase abbreviations
            ("vb", "VolBreakout"),
            ("im", "IntradayMomentum"),
            ("pb", "PullbackEntry"),
            # Underscore variants
            ("vol_breakout", "VolBreakout"),
            ("intraday_momentum", "IntradayMomentum"),
            ("pullback_entry", "PullbackEntry"),
            # Case-insensitive
            ("volbreakout", "VolBreakout"),
            ("intradaymomentum", "IntradayMomentum"),
            ("pullbackentry", "PullbackEntry"),
            # None/null
            ("none", "NONE"),
            ("None", "NONE"),
            ("null", "NONE"),
        ],
    )
    def test_alias_mapping(self, input_val, expected):
        d = _make_decision(strategy_used=input_val)
        assert d.strategy_used == expected

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("VolBreakout, IntradayMomentum", "VolBreakout"),
            ("VB, IM", "VolBreakout"),
            ("IntradayMomentum/PullbackEntry", "IntradayMomentum"),
            ("PB and VB", "PullbackEntry"),
            ("IM & PB", "IntradayMomentum"),
        ],
    )
    def test_multi_strategy_picks_first(self, input_val, expected):
        d = _make_decision(strategy_used=input_val)
        assert d.strategy_used == expected

    def test_none_value_passthrough(self):
        d = _make_decision(strategy_used=None)
        assert d.strategy_used is None

    def test_whitespace_stripped(self):
        d = _make_decision(strategy_used="  VolBreakout  ")
        assert d.strategy_used == "VolBreakout"

    def test_unknown_strategy_passthrough(self):
        d = _make_decision(strategy_used="MeanReversion")
        assert d.strategy_used == "MeanReversion"


class TestPromptStrategyInstruction:
    """System prompt contains basic decision instructions."""

    def test_system_prompt_has_decision_types(self):
        from tradememory.replay.prompt import build_system_prompt

        prompt = build_system_prompt()
        assert "BUY" in prompt
        assert "HOLD" in prompt
        assert "JSON" in prompt
