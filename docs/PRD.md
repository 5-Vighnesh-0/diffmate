# DiffMate PRD: AI Pull Request Review Agent

Date: 2026-10-06. Status: draft for review.

## 1. Overview

DiffMate is an AI agent that reviews GitHub pull requests and posts inline comments on likely bugs, security issues, and missing tests. Small teams and solo developers often merge with no second reviewer, so DiffMate gives them a first pass without ever changing their code.

It is also a portfolio project: a deployed system with a measured accuracy result, a dashboard, and a landing page with scroll animation. The stack is Python (FastAPI) for the backend and TypeScript (React with Framer Motion) for the frontend, built over 5 weeks.

## 2. Goals and success metrics

DiffMate succeeds if it finds real bugs on a benchmark of 60 to 100 pull requests, with few false alarms and a low cost per PR.

Goals:

- Review a PR automatically within minutes of it being opened
- Post a handful of high-confidence inline comments, never a flood
- Prove quality with a repeatable benchmark, not a hand-picked demo
- Ship a live demo, dashboard, and landing page by the end of week 5

Non-goals for v1: auto-fixing code, managing many repos or orgs, fine-tuning models, and languages beyond Python and TypeScript.

| Metric | Starting target | How it is measured |
| --- | --- | --- |
| Precision (posted findings that are real) | 70% or higher | Benchmark labels and accept/reject clicks |
| Recall on seeded bugs | 60% or higher | Benchmark with known bugs |
| False positives per PR | 1 or fewer | Benchmark |
| Cost per PR | $0.10 or less | Token logs per run |
| Time to first comment (median) | 2 minutes or less | Run timestamps |

These targets are starting guesses. Set the final values after the first benchmark run.

## 3. Users and use cases

The primary users are small dev teams, student teams, and solo developers on GitHub who have no dedicated reviewer. The second audience is recruiters and interviewers, who judge the project from the landing page, the repo, and the benchmark results.

| User | Need | What they do |
| --- | --- | --- |
| Solo developer or student team | A second set of eyes before merging | Installs the GitHub App on a repo, opens PRs, reads inline comments |
| Maintainer of a small repo | Faster triage of incoming PRs | Uses the dashboard to see findings per PR and mark them useful or not |
| Recruiter or interviewer | A quick read on engineering depth | Scrolls the landing page, opens the live demo and the benchmark results |

## 4. Functional requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| F1 | A GitHub App receives PR opened and updated webhooks and verifies the signature | Must |
| F2 | Jobs go into a queue; the worker retries failures and runs once per commit | Must |
| F3 | The worker gathers the diff and runs linters (ruff for Python, ESLint for TypeScript) first | Must |
| F4 | The agent loop has tools to read a file, search the repo, view a diff hunk, and list related tests, with limits on steps and tokens | Must |
| F5 | Findings use a fixed format: file, line, category, severity, confidence, explanation | Must |
| F6 | Duplicates and low-confidence findings are dropped; at most 5 inline review comments per PR are posted | Must |
| F7 | The dashboard shows runs, a step-by-step agent trace, and findings with accept and reject buttons | Must |
| F8 | A benchmark runner replays PRs and scores precision, recall, cost, and latency | Must |
| F9 | A landing page has a scroll-driven walkthrough of the pipeline and a results section | Should |
| F10 | Framer Motion is used across the app, including page transitions, with a reduced-motion fallback | Should |

## 5. Non-functional requirements and guardrails

The agent can only read and comment, it treats PR content as untrusted, and its cost is capped.

- **Security:** verify the webhook signature on every request. The GitHub App is read-only on repository contents and can only post comments. Secrets live in environment variables and are never logged.
- **Prompt injection:** PR titles, descriptions, code, and comments are untrusted data. The agent has no tool that writes files, runs code, or sends data out. Test with PRs that contain planted instructions.
- **Cost control:** a hard cap on steps and tokens per run, and a daily spend limit that pauses new runs.
- **Reliability:** one run per commit, retries with backoff, and failed runs shown in the dashboard.
- **Data stored:** findings and trace metadata only, not full copies of repository files.
- **Performance and accessibility:** animate only transform and opacity, honor the reduced-motion setting, keep the dashboard keyboard-navigable, and aim for a Lighthouse performance score of 90 or higher.

## 6. Architecture and tech stack

See [architecture.md](architecture.md) for the diagram and data flow.

| Layer | Choice (proposed) |
| --- | --- |
| Backend | Python, FastAPI |
| Queue | Redis |
| Database | Postgres |
| Frontend | TypeScript, React, Framer Motion |
| Agent | LLM provider API with tool use (provider not chosen yet) |
| Checks and CI | ruff, ESLint, GitHub Actions |
| Packaging | Docker (hosting not chosen yet) |

## 7. Evaluation plan

Quality is measured on a benchmark of 60 to 100 PRs with known answers, run against three setups. Details in [benchmark.md](benchmark.md).

| Setup | What it is | Why it is included |
| --- | --- | --- |
| 1. Linter only | ruff and ESLint warnings turned into comments | The baseline to beat |
| 2. Agent only | The LLM agent with tools and no filtering | Shows raw agent behavior |
| 3. Agent plus filtering | Full DiffMate with confidence filter, dedupe, and comment cap | The actual product |

Rules: freeze the benchmark before tuning prompts, and hold out about 20% of it for a final untouched run. The gap between setups 1 and 3 is the headline resume number.

## 8. Landing page and motion design

A public landing page tells the project story with scroll-driven motion, and Framer Motion adds consistent movement across the whole app. The full spec is in [DESIGN.md](DESIGN.md).

| Area | Motion | Framer Motion tools |
| --- | --- | --- |
| Hero | Headline and buttons fade and slide in one after another | Variants with staggered children |
| Pipeline walkthrough | The diagram builds step by step as you scroll; a progress line follows the scroll position | useScroll, useTransform |
| Results | Benchmark numbers count up when they scroll into view | whileInView |
| Dashboard | Agent trace steps appear one by one; list rows animate in and out | AnimatePresence, layout animations |
| Page transitions | Routes cross-fade or slide | AnimatePresence |

Rules: animate only transform and opacity, keep durations between 0.2 and 0.6 seconds, never let motion block reading or clicking, and turn motion off for people who set reduced motion.

## 9. Timeline

The plan assumes a start on 2026-10-07. Week 5 is the polish week. See [PLAN.md](PLAN.md) for tasks.

| Week | Dates | Milestone |
| --- | --- | --- |
| 1 | Oct 7 to Oct 13 | Webhook and queue, first comment posted |
| 2 | Oct 14 to Oct 20 | Agent loop and tools |
| 3 | Oct 21 to Oct 27 | Guardrails, auth, security, structured findings |
| 4 | Oct 28 to Nov 3 | Benchmark and evaluation (benchmark frozen Oct 30) |
| 5 | Nov 4 to Nov 10 | Dashboard, landing page, motion, demo live Nov 10 |

If time runs short, cut in this order: page transitions, dashboard motion, landing-page extras. The benchmark stays.

## 10. Risks, open questions, and resume deliverables

| Risk | Mitigation |
| --- | --- |
| Flaky agent output | Structured output, confidence filter, and the benchmark |
| Runaway cost | Step and token caps, plus a daily spend limit |
| Prompt injection from PR content | Read-only tools and tests with planted instructions |
| Too much scope (agent, benchmark, dashboard, motion everywhere) | Cut page transitions first, then dashboard motion, then landing extras; never cut the benchmark |
| GitHub App and hosting setup friction | Demo on your own repos and start the setup in week 1 |

Open questions:

- Which LLM provider and model?
- Where to host the backend, Redis, Postgres, and frontend?
- Which open-source repos supply the benchmark PRs?
- Is DiffMate the final name?

Resume deliverables:

- Live demo link and a GitHub repo with README and architecture diagram
- Benchmark results table and a 60 to 90 second demo video
- Three resume bullets written from the real numbers, in this shape: "Built DiffMate, an AI PR review agent (FastAPI, React, Redis, Postgres) that reached X% precision and Y% recall on a Z-PR benchmark at $N per PR"
