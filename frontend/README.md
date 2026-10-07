# Frontend

TypeScript, React, Vite, Framer Motion. Design spec: `../docs/DESIGN.md`.

## Layout

```
src/
  routes/       landing, dashboard, run detail
  scenes/       landing page scroll scenes
  motion/       shared motion tokens and helpers
  components/
  lib/          API client
  styles/       tokens (colors, fonts)
tests/
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
