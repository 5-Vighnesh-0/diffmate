# BRIEF: DiffMate landing page

Interviewed 2026-10-21 (Vighnesh, multiple-choice answers in chat). Scope: landing page only, $0, no generated imagery or video. The dashboard is out of scope and stays as built.

## Subject

DiffMate: a GitHub App that reviews pull requests and leaves at most five inline comments. Audience: developers on small teams, and recruiters judging the project. The page exists to install one belief: **when DiffMate speaks, it is right, and it tells you how often it stays quiet.** Next action, one label everywhere: **Install on GitHub** (until there is a public App link: **Open the dashboard**).

## The eight topics

1. **Vibe:** "Loud, brutalist." No references given.
2. **Journey (chosen order):** hook > the code writes itself > the catch > honest numbers > plant your own bug > install.
3. **Energy:** "Calm start, intense middle, calm close."
4. **Feeling and the one moment:** "Watching it catch the bug." Stage-by-stage feeling authored below from that answer.
5. **The thing no other site does:** "could you add both 1 and 2", meaning (1) *you plant the bug* and (2) *scroll writes the code*. Resolved: (2) is the signature move and carries the peak; (1) is the closing input.
6. **Range from premium-minimal:** brutalist, pushed within DESIGN.md: "Push DESIGN.md harder" (paper, ink, signal red, Anton, Inter, JetBrains Mono).
7. **One world or distinct scenes:** "Distinct scenes."
8. **Assets:** none (no photography or footage). Every visual is real code, real AI output, or real numbers. The $0 rule forbids generated imagery.

## Grammar: Live surface

The page behaves like the product: a pull request being written and reviewed, driven by scroll. Why the others lost:
- Filmic one-shot: needs continuous footage we do not have, and hides the product behind a film.
- Chaptered editorial and typographic poster: a reading or slogan page; DiffMate's argument is a demo, not prose.
- Continuous world: needs a place to travel through; a code review has no geography.
- Gallery: DiffMate is one thing, not a range.
- Split stage: tempting (code before vs after), but the honest result is not a two-sided contest.
- Rhythmic cutlist: energy brand pacing; the peak needs a long hold.

**Brutalist inside the surface.** Live surface bans marketing headings, so the loudness comes from the surface itself: code set at display scale, raw 2px ink rules, full-bleed red and ink blocks, real numbers at Anton display size.

**Honesty rule.** Every comment, trace step and number is real: the review on the page and the four "plant a bug" results are recorded from actual DiffMate runs (Gemini Flash Lite, free tier) and labelled with their date. The numbers come from `frontend/src/lib/benchmark.json`.

## Feeling curve (written before the acts)

```
1  Recognition   a pull request page, quiet, "waiting for review": every developer has stared at this
2  Anticipation  the code arrives line by line under the visitor's own scroll, large and plain
3  Tension       one line goes in that looks fine; the AI starts reading around it, step by step
4  Release (PEAK) the red block slams across that exact line and the comment lands on it
5  Trust         the real numbers, including the misses, said plainly
6  Agency        the visitor breaks a line themselves and sees what DiffMate actually said
7  Resolve       one line, one link, the page goes still
```

**The peak:** "I scrolled, it wrote the code, and the red bar hit the exact line with the bug." Lives in the pinned review act; it gets the largest scroll span on the page, and the trace steps before it are deliberately slow and small.

**It's the site where** your scroll writes a pull request and you watch an AI catch the bug in it.

**Authored silence:** a short hold after the comment lands (end of the peak act) before the numbers start. Not dead scroll.

## Score

| Beat | Feeling | Device | Why |
| --- | --- | --- | --- |
| Hook | Recognition | `flow` (static surface in a state) | Calm start: nothing moves until the visitor does |
| Writes + catch | Anticipation, tension, release | `pin` driven by scroll progress (signature move) | The longest act; one held frame where state advances |
| Numbers | Trust | `count` + table | Real figures, counted once |
| Plant a bug | Agency | pointer / real input | Live-surface close: an input, not a button island |
| Install | Resolve | plain line + link | Quiet after the loud middle |

Four device families, none repeated in a row. Total length about 6 viewport-heights, with the pinned act at about 3.5.

## Build report (2026-10-21)

- **Grammar:** live surface, brutalist family. Why the other seven lost: above.
- **Signature move:** the visitor's scroll types the pull request line by line at display size; the AI's real steps appear; a hard full-width red bar crosses the buggy line and the real comment lands. Not a kit device: it is page code driven by scroll progress.
- **Fingerprint gate:** registry was empty (first build), so nothing to clear. Row appended to `scrollcraft/FINGERPRINTS.md`.
- **Generated assets:** none ($0 rule). Real content instead: four reviews recorded by `python -m benchmark.demo` on 2026-10-21 (Gemini Flash Lite, 15 requests, all four caught their bug) and the benchmark numbers.
- **Engine:** scroll-craft's HTML engine not used; the page is the existing React + motion app, so the method was applied without the mechanism.
- **Feel check (scrolled cold at 1280x800, one word per act):** hook *recognition*; writing *anticipation*; trace *tension* (quiet, small, as intended); red bar *release*; numbers *trust*; plant a bug *agency*; close *resolve*. Matches the intended curve. The peak holds the largest span (the 400vh pinned track).
- **Verified (built-in browser screenshots):** 1280x800 at review progress 0.3, 0.6, 0.95; numbers; plant-a-bug with the shell choice; 375px phone (still layout, whole review visible, no sideways scroll). Fixed during verification: the comment showed faintly before its moment; the longest code line was cut off; the three giant numbers collided; "Try it" wrapped in the phone bar.
- **Lighthouse 12 (production build):** performance 96, accessibility 100 (LCP 2.3 s, TBT 50 ms, CLS 0.003).
- **Not verified:** scroll-craft's own harness (`shoot.mjs`: dead-scroll and composited-contrast checks) was not run, because it needs `playwright-core` installed; a real phone.
