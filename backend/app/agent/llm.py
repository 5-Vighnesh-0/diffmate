"""The one place that talks to the LLM provider (ADR 0003). Provider/model come from env."""

import asyncio
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import types


class LlmError(RuntimeError):
    """Provider failure. Kept apart from httpx errors so it is never retried as a GitHub error."""


class LlmRateLimited(LlmError):
    """Google answered 429 (per-minute or per-day free-tier limit): pause, don't keep retrying."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LlmStep:
    calls: list[ToolCall]
    text: str
    tokens_in: int
    tokens_out: int
    raw: list[dict]  # model steps, appended to the history unchanged (stateless mode)


class GeminiLLM:
    def __init__(
        self, api_key: str, model: str, thinking_level: str = "low", timeout_seconds: float = 90
    ):
        # The SDK retries only real server hiccups. A 429 must come back at once: its
        # Retry-After can be hours on the free tier, and the run should pause instead.
        retry = types.HttpRetryOptions(attempts=1, http_status_codes=[500, 502, 503, 504])
        self.client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(retry_options=retry)
        )
        self.model = model
        # Default (deep) thinking took ~55 s per call on the free tier; "low" took ~4 s.
        self.thinking_level = thinking_level
        self.timeout_seconds = timeout_seconds

    async def step(
        self, system: str, history: list, tools: list, max_output_tokens: int
    ) -> LlmStep:
        request = self.client.aio.interactions.create(
            model=self.model,
            system_instruction=system,
            input=history,
            tools=tools,
            store=False,  # Google keeps no copy of the conversation; we resend the history
            generation_config={
                "max_output_tokens": max_output_tokens,
                "thinking_level": self.thinking_level,
            },
        )
        try:
            interaction = await asyncio.wait_for(request, self.timeout_seconds)
        except (TimeoutError, asyncio.CancelledError):
            raise
        except Exception as e:
            # The SDK has several error classes; all carry the HTTP status as `status_code`
            # (compat RateLimitError, GenAiError) or `code` (errors.APIError).
            status = getattr(e, "status_code", None) or getattr(e, "code", None)
            if status == 429:
                raise LlmRateLimited("429") from e
            raise LlmError(type(e).__name__) from e
        steps = [
            s for s in interaction.steps or [] if s.type not in ("user_input", "function_result")
        ]
        calls = [
            ToolCall(s.id, s.name, dict(s.arguments)) for s in steps if s.type == "function_call"
        ]
        usage = interaction.usage
        return LlmStep(
            calls=calls,
            text=interaction.output_text or "",
            tokens_in=(usage.total_input_tokens or 0) if usage else 0,
            # Thinking is billed as output, so it counts against the cap and the estimate.
            tokens_out=(
                (usage.total_output_tokens or 0) + (getattr(usage, "total_thought_tokens", 0) or 0)
                if usage
                else 0
            ),
            raw=[s.model_dump(mode="json", exclude_none=True) for s in steps],
        )
