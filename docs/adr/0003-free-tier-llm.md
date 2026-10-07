# ADR 0003: Free-tier LLM and the $0 rule

**Status:** Accepted (2026-10-06)
**Date:** 2026-10-06
**Deciders:** Vighnesh

## Context

The project must never spend money. A Claude Pro subscription does not include API access; API use is billed separately on prepaid credits. The agent needs a model that handles multi-step tool calling over code. The dev laptop (14 GB RAM, 4 GB GTX 1650) can only run small local models.

## Decision

- Use the **Google Gemini API free tier**, model `gemini-3.8-flash`, through the official `google-genai` SDK.
- Provider and model come from env (`LLM_PROVIDER`, `LLM_MODEL`), so a switch later is a config change plus one client module, not a rewrite.
- **$0 is enforced, not just documented:**
  - The API key is created in a Google project with **no billing account attached**, so usage cannot be charged.
  - `LLM_DAILY_REQUEST_CAP` stops new LLM calls for the day when reached; runs are marked "paused: daily cap".
  - Per-run step and token caps (ADR 0002) still apply.
- Cost per PR is reported as an **estimate**: logged tokens × public list price (Gemini 3.8 Flash paid tier, $0.75 in / $3.75 out per 1M tokens, checked 2026-10-06), always labelled "estimated".

## Options considered

| Option | Cost | Quality for tool use | Limits | Notes |
| --- | --- | --- | --- | --- |
| **Gemini free tier** (picked) | $0 | Good (current Flash model) | Per-account RPM/RPD, shown in AI Studio | Free-tier prompts may be used to improve Google products |
| NVIDIA build.nvidia.com | $0 | Good (many open models) | ~1,000 credits, ~40 RPM (third-party sources) | Credits run out; OpenAI-compatible API |
| Local Ollama | $0 | Weak on 4 GB GPU (~7B models) | Hardware-bound | Private; slow |
| Claude API (Opus 5.5) | ~$0.10–0.20 per PR | Strong | Paid | Not allowed by the $0 rule |

## Trade-offs

- Free tier keeps cost at zero but caps throughput: the benchmark must be resumable and spread across days.
- Free-tier data may be used by Google: only public, open-source code is reviewed on this key. This goes in the threat model and the README.
- Setup 3 reuses setup 2's agent output (filter only), so one agent run per PR serves both setups and halves LLM usage.

## Consequences

- Easier: zero spend; one SDK.
- Harder: rate-limit handling (back off on 429, resume the benchmark); results depend on a free model.
- Revisit: if the user gets credits, compare another model on the frozen benchmark (config change only).

## Action items

1. [ ] User creates a Gemini API key in AI Studio in a project with no billing, and sets `GEMINI_API_KEY` in their own `.env`
2. [ ] User reads free-tier limits in AI Studio → Rate limits; `LLM_DAILY_REQUEST_CAP` is set below the daily limit
3. [ ] Phase 2: LLM client enforces the cap; a unit test proves calls stop at the cap

## Update 2026-10-07: measured free-tier limits

From the AI Studio rate-limit page (user's account) and live calls:

| Model | RPM | TPM | RPD | Measured latency (tiny call) |
| --- | --- | --- | --- | --- |
| gemini-3.8-flash (chosen) | 5 | 250K | **20** | ~55 s default thinking, ~4 s with `thinking_level: low` |
| gemini-3.5-flash-lite | 15 | 250K | 500 | ~0.7 s |

Consequences, decided with Vighnesh:
- Stay on `gemini-3.8-flash`. `LLM_DAILY_REQUEST_CAP=16` (80% of 20), `LLM_REQUESTS_PER_MINUTE=4` (calls are spaced so the 5 RPM limit is never hit).
- `thinking_level: low` by default (measured 13x faster).
- A Google 429 is not retried by the SDK; the run stops at once and is marked `paused_daily_cap`. Only 500/502/503/504 get one SDK retry.
- At ~5 requests per review this is about 3 reviews per day. The Phase 4 benchmark (~300 requests) does not fit one week at this rate: options are put to the Phase 2 gate.

