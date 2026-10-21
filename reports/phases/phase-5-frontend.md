# Phase 5: Frontend

**Dates:** 2026-10-21 to (open)
**Status:** in progress (live check and Lighthouse pending)

## Decisions (Vighnesh, 2026-10-21)

Dashboard first; landing with only DESIGN.md's never-cut effects; History API routing instead of react-router; fonts self-hosted (@fontsource); Vitest + Testing Library; benchmark numbers bundled as JSON instead of a `/api/benchmark/summary` endpoint (pushback accepted: the numbers only change when the benchmark is re-run).

## What was built

- Dashboard (`/dashboard`): sign-in prompt when signed out; reviews list with status, comment count, AI requests, "Show older"; free-quota line; sign out (CSRF).
- Review detail (`/dashboard/runs/:id`): every finding with file, line, severity, confidence and whether it was posted or why not; AI text rendered as plain text; Useful / Not useful votes with the CSRF token, visible error if a vote fails; the agent's steps.
- Landing (`/`): hero diff card that tilts upright on scroll (T5); five-step pinned pipeline story with hard-edged panel wipes (T1, T2); results counted up from the real benchmark (T7) and a three-setup table; closing call to action.
- Reduced motion or screens under 640px: one live media query switches to a still layout (scenes stacked, hero card under the headline).
- `make bench-score` also writes `frontend/src/lib/benchmark.json`; the landing imports it.
- Packages (all pre-approved in PLAN): motion, @fontsource/anton, @fontsource/inter, @fontsource/jetbrains-mono, vitest, jsdom, @testing-library/react. `pnpm audit`: no known vulnerabilities.

## Checks so far

```
make test   → backend 185 passed · frontend 4 passed
pnpm build  → built, no type errors
```

Browser checks (built-in browser): desktop and 375px phone; tilt, pinned wipes, counters, results table; no horizontal scroll on phone; no console errors except the expected 401 from the signed-out dashboard.

## Problems found and fixed while building

- Tests caught a real bug: the stacked (reduced-motion / phone) pipeline still set up scroll tracking on an element it never rendered, so motion threw. Scroll tracking moved into the pinned-only component.
- "Narrow screen" was measured once at first render; a pane opened narrow stayed in the still layout after widening. Now a live media query.
- Inherited text colours: the step-5 comment and the step-4 diff card were unreadable inside red and dark scenes. Both now set their own ink colour.
- Contrast: ink on signal red is 4.2:1, below 4.5:1 for body text, so red sections use white text (4.7:1).
- On phones the diff card overflowed and the red marker covered code; long lines now scroll inside the card and the marker sits in the gutter.

## Open for the gate

- Live check: sign in and vote on a real review (needs Vighnesh's GitHub login; the built-in browser cannot sign in for you).
- Lighthouse performance score (needs the Lighthouse tool, a one-off download).
- 15 empty placeholder files from Phase 0 are now unused (deleting needs approval).
