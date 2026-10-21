# Phase 5: Frontend

**Dates:** 2026-10-21
**Status:** awaiting approval

## Decisions (Vighnesh, 2026-10-21)

Dashboard first; landing with only DESIGN.md's never-cut effects; History API routing instead of react-router; fonts self-hosted (@fontsource); Vitest + Testing Library; benchmark numbers bundled as JSON instead of a `/api/benchmark/summary` endpoint (pushback accepted: the numbers only change when the benchmark is re-run).

## What was built

- Dashboard (`/dashboard`): sign-in prompt when signed out; reviews list with status, comment count, AI requests, "Show older"; free-quota line; sign out (CSRF).
- Review detail (`/dashboard/runs/:id`): every finding with file, line, severity, confidence and whether it was posted or why not; AI text rendered as plain text; Useful / Not useful votes with the CSRF token, visible error if a vote fails; the agent's steps.
- Landing (`/`), first version: tilting hero card (T5), pinned five-step story (T1, T2), counted results (T7). Replaced the same day (below).
- Reduced motion or screens under 640px: one live media query switches to a still layout (scenes stacked, hero card under the headline).
- `make bench-score` also writes `frontend/src/lib/benchmark.json`; the landing imports it.
- Packages (all pre-approved in PLAN): motion, @fontsource/anton, @fontsource/inter, @fontsource/jetbrains-mono, vitest, jsdom, @testing-library/react. `pnpm audit`: no known vulnerabilities.

## Landing rebuilt with scroll-craft (Vighnesh, 2026-10-21)

Vighnesh asked to use scroll-craft. Pushback accepted: its paid image generation is off ($0 rule), and the dashboard keeps its calm design. Interview answers: loud, brutalist; peak = watching it catch the bug; signature = scroll writes the code (peak) plus plant a bug (close); calm-intense-calm; distinct scenes; push DESIGN.md harder; real recorded results.

- Grammar: live surface. Acts: PR page waiting (calm) > pinned 400vh act where scroll types `stats.py`, the AI's real steps appear, a red bar slams across line 8 and the real comment lands (peak) > real numbers at display size > plant a bug (radio input, four real recorded reviews, labelled "Recorded 2026-10-21 … Not live") > one quiet line.
- `benchmark/demo.py` records the reviews (15 free Flash Lite requests; all four caught their bug) into `frontend/src/lib/demo.json`; it refuses to write if any run did not finish.
- Verified in the built-in browser at 1280x800 and 375px; Lighthouse 96 / 100. Feel check matches the brief. scroll-craft's own screenshot harness not run (needs playwright-core).

## Checks so far

```
make test   → backend 185 passed · frontend 5 passed (vote test now also checks the explanation, the count, the GitHub link and "Saved")
pnpm build  → built, no type errors
```

Lighthouse 12 (production build, `vite preview`, default phone settings, Playwright's Chromium):

| Page | Performance | Accessibility | LCP | TBT | CLS |
| --- | --- | --- | --- | --- | --- |
| Landing `/` | 95 | 100 | 2.2 s | 260 ms | 0.029 |
| Dashboard `/dashboard` (signed out) | 97 | 100 | 2.3 s | 0 ms | 0 |

The first landing run scored accessibility 95: the finding marker had an `aria-label` on an element with no role. Fixed with `role="img"`; re-run gave 95 / 100 (landing LCP/TBT above are from the first run).

Browser checks (built-in browser): desktop and 375px phone; tilt, pinned wipes, counters, results table; no horizontal scroll on phone; no console errors except the expected 401 from the signed-out dashboard.

## Problems found and fixed while building

- Tests caught a real bug: the stacked (reduced-motion / phone) pipeline still set up scroll tracking on an element it never rendered, so motion threw. Scroll tracking moved into the pinned-only component.
- "Narrow screen" was measured once at first render; a pane opened narrow stayed in the still layout after widening. Now a live media query.
- Inherited text colours: the step-5 comment and the step-4 diff card were unreadable inside red and dark scenes. Both now set their own ink colour.
- Contrast: ink on signal red is 4.2:1, below 4.5:1 for body text, so red sections use white text (4.7:1).
- On phones the diff card overflowed and the red marker covered code; long lines now scroll inside the card and the marker sits in the gutter.

Cleanup (approved by Vighnesh): 15 empty placeholder files from Phase 0 deleted with `git rm` after confirming each was empty and unreferenced.

## Live check and follow-up (Vighnesh, 2026-10-21)

Vighnesh signed in with GitHub in Firefox and used the dashboard: all features work, colours and the scroll-typing landing kept as they are. Feedback: after signing in it does not explain what is happening ("what am I supposed to do"), and it could use more animation. Changes:
- Reviews list: intro (what a review is, where it comes from), status legend, rows arrive in a short stagger.
- Review page: intro (found vs posted vs held back), plain explanation of Useful / Not useful (saved only in DiffMate, used to measure accuracy, changeable), "Saved" confirmation and "You have rated n of m", link to the pull request on GitHub, "What next?" (push a fix, a new review appears), comment cards and steps arrive in a stagger.
- Page changes fade in (CSS, no exit wait; disabled with reduced motion). A first version with motion's AnimatePresence "wait" left the old page on screen whenever animation frames were paused (seen in the test browser); replaced with the CSS fade.

- Sign-in screen (Vighnesh: "what am I supposed to do?"): headline, purpose, button above the fold, three-step "What happens next", privacy note matching the real login (token never stored, never posts as you, 8 h), and a real recorded review as the example.

- Plain language for beginners (Vighnesh): reviews list explains how a review happens, counts reviews and notes, shows each review as a sentence, and defines the three words people meet; a review explains each note without jargon and lists the AI's steps in words.

## Acceptance checks at the gate (with output)

```
make test          → backend 185 passed · frontend 6 passed
ruff               → clean
pnpm build / audit → built · No known vulnerabilities found
Lighthouse 12      → landing 94 perf / 100 a11y · dashboard (sign-in screen) 96 / 100
```

- [x] Lighthouse performance 90 or higher
- [x] Reduced motion verified (test: still layout with the whole review visible; browser check at 375px)
- [x] Live check by Vighnesh (signed in, voted, gave feedback; all feedback addressed)

## Open for the gate

- The App's public install link (`github.com/apps/<name>`): needed in Phase 6 to let others install DiffMate.
- Not verified: a real phone; scroll-craft's own screenshot harness.
