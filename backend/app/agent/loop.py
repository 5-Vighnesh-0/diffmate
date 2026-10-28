import asyncio
import json
import time
from dataclasses import dataclass, field

from app.agent.budget import Budget, DailyCap
from app.agent.guardrails import SUBMIT_TOOL, parse_submission, wrap_untrusted
from app.agent.llm import LlmRateLimited
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.schemas import Finding
from app.agent.tools import Tools

MAX_OUTPUT_TOKENS = 4096
MAX_CALLS_PER_STEP = 5


@dataclass
class TraceEntry:
    step_no: int
    tool: str
    summary: str  # tool name and arguments only, never file contents
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0


@dataclass
class AgentResult:
    findings: list[Finding]
    invalid: int
    trace: list[TraceEntry]
    budget: Budget
    stop_reason: str  # submitted|step_cap|token_cap|daily_cap|rate_limited|no_submission
    llm_requests: int = 0


@dataclass
class _State:
    trace: list[TraceEntry] = field(default_factory=list)
    requests: int = 0


def with_second_look(first: AgentResult, second: AgentResult) -> AgentResult:
    """One run's result from both passes. The first pass's stop reason stands: if the second
    look is cut short (daily cap, step cap), the first pass's clean answer is still valid."""
    b = first.budget
    b.tokens_in += second.budget.tokens_in
    b.tokens_out += second.budget.tokens_out
    return AgentResult(
        first.findings + second.findings,
        first.invalid + second.invalid,
        first.trace + second.trace,
        b,
        first.stop_reason,
        first.llm_requests + second.llm_requests,
    )


def _summary(name: str, args: dict) -> str:
    if name == "submit_findings":
        items = args.get("findings")
        return f"submit_findings({len(items) if isinstance(items, list) else 0} findings)"
    shown = ", ".join(f"{k}={json.dumps(v)[:80]}" for k, v in args.items())
    return f"{name}({shown})"[:500]


def _user(text: str) -> dict:
    return {"type": "user_input", "content": [{"type": "text", "text": text}]}


def _result(call, output: str) -> dict:
    return {
        "type": "function_result",
        "name": call.name,
        "call_id": call.id,
        "result": [{"type": "text", "text": output}],
    }


async def run_agent(llm, tools: Tools, context: str, budget: Budget, cap: DailyCap) -> AgentResult:
    history = [_user(context)]
    s = _State()

    def done(reason: str, findings=None, invalid=0) -> AgentResult:
        return AgentResult(findings or [], invalid, s.trace, budget, reason, s.requests)

    while True:
        if budget.steps >= budget.max_steps:
            return done("step_cap")
        # Next call's input is at least the last one (history only grows): never start a call
        # that could push the run past its token cap.
        # chars/3 over-estimates code tokens on purpose: safer than undercounting.
        estimate = max(len(json.dumps(history)) // 3, budget.last_tokens_in) + MAX_OUTPUT_TOKENS
        if budget.tokens + estimate > budget.max_tokens:
            return done("token_cap")
        if not await cap.take():
            return done("daily_cap")

        last_step = budget.steps == budget.max_steps - 1
        offered = [SUBMIT_TOOL] if last_step else [*tools.declarations(), SUBMIT_TOOL]
        started = time.monotonic()
        try:
            step = await llm.step(SYSTEM_PROMPT, history, offered, MAX_OUTPUT_TOKENS)
        except LlmRateLimited:
            return done("rate_limited")
        s.requests += 1
        budget.charge(step.tokens_in, step.tokens_out)
        history += step.raw
        if not step.calls:
            return done("no_submission")

        offered_names = {t["name"] for t in offered}
        for i, call in enumerate(step.calls):
            entry = TraceEntry(budget.steps, call.name, _summary(call.name, call.arguments))
            if i == 0:  # a step's tokens and time belong to its first call
                entry.tokens_in, entry.tokens_out = step.tokens_in, step.tokens_out
                entry.duration_ms = int((time.monotonic() - started) * 1000)
            s.trace.append(entry)
            if call.name == "submit_findings":
                findings, invalid = parse_submission(call.arguments)
                return done("submitted", findings, invalid)
            if i >= MAX_CALLS_PER_STEP:
                entry.summary = f"refused: too many calls in one step ({call.name})"[:500]
                output = f"error: at most {MAX_CALLS_PER_STEP} tool calls per step"
            elif call.name not in offered_names:
                entry.summary = f"refused: unknown tool {call.name}"[:500]
                output = f"error: unknown tool {call.name!r}; use only the tools provided"
            else:
                # File contents and search hits come from the PR: data, never instructions.
                raw = await asyncio.to_thread(tools.call, call.name, call.arguments)
                output = wrap_untrusted(f"tool:{call.name}", raw)
            history.append(_result(call, output))
