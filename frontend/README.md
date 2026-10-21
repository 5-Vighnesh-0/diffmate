# Frontend

TypeScript, React, Vite, Framer Motion. Design spec: `../docs/DESIGN.md`.

## Layout

```
src/
  routes/       Landing (all landing scenes), Dashboard, RunDetail
  components/ui Shell: sign-in state, quota, sign out
  motion/       motion tokens
  lib/          API client, ~30-line router, benchmark.json (written by `make bench-score`)
  styles/       tokens.css: colors, type, all styles
tests/unit/     Vitest + Testing Library (`pnpm test`)
```

## Rules

- Tokens, fonts, and transitions follow `docs/DESIGN.md` exactly.
- Animate only `transform` and `opacity`.
- Wrap the app in `MotionConfig reducedMotion="user"`; provide a stacked no-motion layout.
- Native scroll with `position: sticky`; never hijack the wheel.
- Render finding text as plain text, never HTML.

## Run

```bash
npm run dev
npm test
```

Exact scripts are confirmed when the app is scaffolded.
