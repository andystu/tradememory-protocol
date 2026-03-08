"""Unified LLM client supporting DeepSeek and Claude via instructor library."""

import logging
import os
from typing import TypeVar

import instructor
from anthropic import Anthropic
from openai import OpenAI

from src.tradememory.replay.models import AgentDecision, DecisionType, ReplayConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Cost per million tokens (USD)
_COST_TABLE = {
    "deepseek": {"input": 0.27, "output": 1.10},
    "claude": {"input": 3.00, "output": 15.00},
}

_DEFAULT_MODELS = {
    "deepseek": "deepseek-chat",
    "claude": "claude-sonnet-4-6",
}


class LLMClient:
    """Unified LLM client wrapping DeepSeek (OpenAI-compatible) and Claude Sonnet."""

    def __init__(self, config: ReplayConfig) -> None:
        self.provider = config.llm_provider
        self.model = config.llm_model or _DEFAULT_MODELS[self.provider]
        self.total_tokens_used: int = 0
        self.total_cost_usd: float = 0.0

        api_key = os.environ[config.api_key_env]

        if self.provider == "deepseek":
            self.client = instructor.from_openai(
                OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            )
        elif self.provider == "claude":
            self.client = instructor.from_anthropic(Anthropic(api_key=api_key))
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def decide(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[T] = AgentDecision,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> T:
        """Call LLM and return structured AgentDecision (or fallback HOLD on error)."""
        try:
            if self.provider == "deepseek":
                result, completion = self.client.chat.completions.create_with_completion(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_model=response_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                usage = completion.usage
                if usage:
                    input_tokens = usage.prompt_tokens or 0
                    output_tokens = usage.completion_tokens or 0
                    self._track_cost(input_tokens, output_tokens)

            else:  # claude
                result, raw = self.client.messages.create_with_completion(
                    model=self.model,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    response_model=response_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if raw.usage:
                    self._track_cost(raw.usage.input_tokens, raw.usage.output_tokens)

            return result

        except Exception as e:
            logger.error(f"LLM API error ({self.provider}): {e}")
            return AgentDecision(
                market_observation="API error — no market data available",
                reasoning_trace=f"LLM API call failed: {e}",
                decision=DecisionType.HOLD,
                confidence=0.0,
            )

    def _track_cost(self, input_tokens: int, output_tokens: int) -> None:
        total = input_tokens + output_tokens
        self.total_tokens_used += total
        costs = _COST_TABLE[self.provider]
        self.total_cost_usd += (
            input_tokens * costs["input"] + output_tokens * costs["output"]
        ) / 1_000_000
