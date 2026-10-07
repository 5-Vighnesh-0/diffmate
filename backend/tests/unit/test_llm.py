import asyncio
from types import SimpleNamespace

import pytest

from app.agent.llm import GeminiLLM


class FakeInteractions:
    def __init__(self, delay=0.0):
        self.delay, self.kwargs = delay, None

    async def create(self, **kwargs):
        self.kwargs = kwargs
        await asyncio.sleep(self.delay)
        step = SimpleNamespace(type="function_call", id="c1", name="submit_findings", arguments={})
        step.model_dump = lambda **_: {"type": "function_call", "id": "c1"}
        usage = SimpleNamespace(total_input_tokens=10, total_output_tokens=2)
        return SimpleNamespace(steps=[step], usage=usage, output_text=None)


def llm_with(fake, timeout=5.0):
    llm = GeminiLLM("key", "gemini-3.8-flash", thinking_level="low", timeout_seconds=timeout)
    llm.client = SimpleNamespace(aio=SimpleNamespace(interactions=fake))
    return llm


async def test_step_is_stateless_and_uses_the_configured_thinking_level():
    fake = FakeInteractions()

    step = await llm_with(fake).step("sys", [], [], 512)

    assert fake.kwargs["store"] is False
    assert fake.kwargs["generation_config"] == {"max_output_tokens": 512, "thinking_level": "low"}
    assert (step.tokens_in, step.tokens_out, step.calls[0].name) == (10, 2, "submit_findings")


async def test_when_only_submit_is_offered_the_model_must_call_it():
    # Dev benchmark 2026-10-07: on the last step Flash Lite often asked for another tool
    # instead of submitting, so 10 of 48 runs ended with no answer (step_cap).
    fake = FakeInteractions()
    submit = {"type": "function", "name": "submit_findings"}

    await llm_with(fake).step("sys", [], [submit], 512)
    assert fake.kwargs["generation_config"]["tool_choice"] == "any"

    await llm_with(fake).step("sys", [], [{"type": "function", "name": "read_file"}, submit], 512)
    assert "tool_choice" not in fake.kwargs["generation_config"]


async def test_a_slow_model_call_times_out_instead_of_hanging():
    with pytest.raises(TimeoutError):
        await llm_with(FakeInteractions(delay=5), timeout=0.1).step("sys", [], [], 512)


async def test_thinking_tokens_count_as_output():
    fake = FakeInteractions()
    llm = llm_with(fake)

    async def create(**kwargs):
        r = await FakeInteractions.create(fake, **kwargs)
        r.usage = SimpleNamespace(
            total_input_tokens=10, total_output_tokens=2, total_thought_tokens=40
        )
        return r

    fake.create = create
    step = await llm.step("sys", [], [], 512)

    assert step.tokens_out == 42


async def test_provider_network_errors_are_not_mistaken_for_github_errors():
    import httpx

    from app.agent.llm import LlmError

    class Down(FakeInteractions):
        async def create(self, **kwargs):
            raise httpx.ConnectError("gemini down")

    with pytest.raises(LlmError):
        await llm_with(Down()).step("sys", [], [], 512)


async def test_google_429_becomes_rate_limited_without_sdk_retries():
    from google.genai import errors

    from app.agent.llm import LlmRateLimited

    class Limited(FakeInteractions):
        async def create(self, **kwargs):
            raise errors.ClientError(429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}})

    with pytest.raises(LlmRateLimited):
        await llm_with(Limited()).step("sys", [], [], 512)


def test_sdk_retries_only_server_errors_never_429():
    llm = GeminiLLM("key", "gemini-3.8-flash")

    retry = llm.client.aio.interactions.sdk_configuration.retry_config
    assert retry.status_codes_override == ["500", "502", "503", "504"]


async def test_sdk_rate_limit_errors_with_status_code_are_rate_limited_too():
    from app.agent.llm import LlmRateLimited

    class RateLimitError(Exception):  # shape of google.genai's compat RateLimitError
        status_code = 429

    class Limited(FakeInteractions):
        async def create(self, **kwargs):
            raise RateLimitError("rate limited")

    with pytest.raises(LlmRateLimited):
        await llm_with(Limited()).step("sys", [], [], 512)
