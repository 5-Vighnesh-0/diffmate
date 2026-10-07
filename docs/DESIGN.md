# DiffMate Design Spec (with scroll transitions)

Design system and motion spec for the DiffMate landing page and dashboard.
Stack: React + TypeScript + Framer Motion. Status: draft for review.

## 1. What the reference videos taught us

Two screen recordings were used as references. Only the motion language and
structure are borrowed. The artwork, characters, copy, and brand names in them
are not reused.

**Video A: illustrated, scroll-driven experience site (about 19s)**
- Every scene fills the viewport and stays pinned while scrolling plays it.
- Scenes change by hard-edged masks, never soft crossfades: rectangular panels
  slide over the previous scene, and a vertical "ink drip" strip pattern
  dissolves white into red (about 6-8s).
- Match cut by zoom: a red circle grows until it becomes the next scene's
  background (about 3-5s).
- Palette is almost only white, black, and one hard red, with one spot accent
  per scene (gold, then green).
- Small outlined caption cards and a round "HOLD" chip float over the scenes.
  The nav is tiny and outlined in the top right.
- Ends on a huge display title with fragments flying out, then a torn-paper
  edge into a red CTA section (about 16-19s).

**Video B: 3D product site built from a prompt (about 18s)**
- Giant condensed headline sits behind a tilted 3D product. As you scroll, the
  product rotates upright and the headline slides away.
- Next sections bring in a stats column (14.5%, 22, 3.62), then a headline
  passing under the product, then photo cards, ink splats, and a glass with a
  ring stain popping in on scroll.
- A horizontal row of items slides in one by one, then the page flips from
  light cream to dark red with a huge wordmark.
- The middle of the video (library site, copy prompt, paste into Claude) is a
  tutorial about the workflow, not design, and is not used here.

## 2. Concept

**"Every diff, on screen."** The reference palette (stark paper, ink, one
saturated red, one spot green) matches code review itself: **red = removed,
green = added.** That gives DiffMate its own identity without copying the
videos.

The landing page is a pinned, scroll-driven story of one pull request moving
through the pipeline. The dashboard stays calm and fast.

## 3. Design tokens

| Token | Value | Use |
| --- | --- | --- |
| `--paper` | `#F3F0E8` | Light background |
| `--ink` | `#0A0A0A` | Text, dark sections |
| `--signal-red` | `#E5120B` | Primary accent, bugs found, headlines |
| `--add-green` | `#7DDB8C` | Added lines, "fixed", success |
| `--deep-red` | `#3A0A0D` | Final section gradient start |
| `--line` | `#0A0A0A` at 12% opacity | Hairlines, card borders |

Rules: one red moment per screen, green only for "added" or success, no
gradients except the final deep-red to ink section.

**Type**
- Display: **Anton** (heavy condensed), uppercase, tight leading (0.9). Hero
  sizes `clamp(4rem, 14vw, 13rem)`.
- Body: **Inter**, 16-18px, line height 1.55.
- Labels and code: **JetBrains Mono**, 12-13px, uppercase labels with 0.08em
  tracking. This replaces the small serif labels in the videos, because
  DiffMate is a developer tool.
- Use tabular numerals for every stat.

**Shape:** 2px radius on cards, hairline borders, no shadows except one soft
shadow under the hero 3D card.

## 4. Motion tokens

| Token | Value |
| --- | --- |
| `dur.fast / base / slow` | 0.2s / 0.4s / 0.6s |
| `ease.out` | `[0.22, 1, 0.36, 1]` |
| `spring.pop` | stiffness 260, damping 22 |
| `spring.scrub` | stiffness 120, damping 30, mass 0.4 (smooths scroll-linked values) |
| `stagger.text / bars` | 0.08s / 0.012s |

Principles:
1. **Hard edges, no soft fades** for scene changes (wipes, bars, zooms).
2. **Animate transform and opacity only.** Wipes use `scaleY`, not `clip-path`.
   Allow `clip-path` only if profiling shows it holds 60fps.
3. **Native scroll only.** Pin with `position: sticky`; never hijack the wheel.
4. One idea per scene. Never run more than two scroll-linked effects at once.

## 5. Page structure and scroll plan

| # | Section | Scroll length | Transitions |
| --- | --- | --- | --- |
| 1 | Hero | 150vh | T5 tilt-to-upright, T6 line reveal |
| 2 | Pipeline story (5 pinned scenes) | 500vh | T1 pinned scrub, T2 panel wipe, T3 zoom match cut |
| 3 | Findings on a real diff | 120vh | T8 splat pop-in |
| 4 | Results | 120vh | T7 counters, T9 row entry |
| 5 | Barcode transition into closing | 80vh | T4 bars, T10 theme flip |
| 6 | Closing CTA (install, repo link) | 100vh | T11 torn edge, T6 line reveal |

**Pipeline story scenes (section 2)**
1. PR opens: a diff card slides in.
2. Job queues: a row of small cards stacks up.
3. Agent investigates: tool calls appear one by one in a trace.
4. Findings: red markers land on the diff lines.
5. Comment posted: the finding becomes an inline review comment.

## 6. Transition catalog

Each entry: where it comes from in the references, what it does, how to build it.

**T1. Pinned scene scrub** (both videos)
Outer wrapper is `N * 100vh` tall; inner stage is `sticky top-0 h-screen`.
Scroll progress drives every scene.

```tsx
const ref = useRef<HTMLDivElement>(null);
const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
const p = useSpring(scrollYProgress, { stiffness: 120, damping: 30, mass: 0.4 });
// scene 2 covers scene 1 between 20% and 40% of the section
const wipe = useTransform(p, [0.2, 0.4], [0, 1]);
```

**T2. Panel wipe** (Video A, rectangular windows)
The next scene sits above the current one and grows from the bottom edge with
a hard edge. `style={{ scaleY: wipe, originY: 1 }}`. Counter-scale the inner
content so it does not stretch.

**T3. Zoom match cut** (Video A, red circle becomes the background)
A red dot in scene 4 (the first finding marker) scales from 1 to about 60 and
becomes the red background of scene 5. Transform scale only, centered on the
dot. Next scene's content fades in at 90% progress.

**T4. Barcode bars** (Video A, vertical ink drip)
24 full-height vertical bars rise with a stagger, covering the screen, then
drop to reveal the next section. Bars look like diff lines and need no assets.
Use 12 bars on mobile.

```tsx
function Bar({ p, i }: { p: MotionValue<number>; i: number }) {
  const s = useTransform(p, [i * 0.008, 0.1 + i * 0.008], [0, 1]);
  return <motion.i style={{ scaleY: s, originY: 1 }} className="bar" />;
}
```

**T5. Tilt to upright** (Video B, bottle rotating while headline leaves)
The hero is a 3D-styled PR card (CSS 3D transform, no WebGL needed at first).
Over the first 100vh: `rotateZ -16deg to 0`, `rotateY -12deg to 0`, `scale
1.15 to 1`. The headline sits behind the card (lower z-index) and moves
`y: 0 to -40vh`, so the card overlaps the letters like the bottle does.

**T6. Line reveal** (Video B, headlines swapping)
Each headline line is wrapped in an `overflow: hidden` mask. The line moves
`y: 105% to 0`, `dur.slow`, `ease.out`, `stagger.text`. Triggered with
`whileInView`, `once: true`.

**T7. Counters** (Video B, stats column)
Numbers count from 0 to the benchmark value over 1.2s with `animate()` and an
ease-out curve. Tabular numerals so digits do not jitter. Reduced motion shows
the final value immediately.

**T8. Splat pop-in** (Video B, ink splats and glass)
Finding markers on the diff pop in: `scale 0 to 1`, `spring.pop`, with a
slight overshoot, `stagger 0.12s`. Rotation comes from a fixed per-marker
value so it looks the same every time.

**T9. Row entry** (Video B, row of cases)
Benchmark PR cards enter from the right: `x: 80 to 0`, `opacity 0 to 1`,
stagger 0.06s, `whileInView`.

**T10. Theme flip** (Video B, cream to dark red)
A fixed dark overlay changes `opacity` with scroll between 0 and 1 across the
barcode section. Do not animate `background-color`, because it repaints.

**T11. Torn edge** (Video A, final section)
A static SVG torn-paper strip sits on the top edge of the closing section and
moves up with `y`, revealing the red CTA beneath it.

**T12. Route transitions** (app-wide)
`AnimatePresence mode="wait"`. Exit: opacity 1 to 0 and `y: 0 to -8`, `dur.fast`.
Enter: opacity 0 to 1 and `y: 8 to 0`, `dur.base`.

**T13. Dashboard micro-motion**
Trace steps appear with stagger 0.04s. Run list uses `layout` animations so
rows slide when the order changes. Accept/reject buttons press with
`whileTap={{ scale: 0.96 }}`. Nothing else moves.

**T14. Cursor chip** (Video A, round HOLD chip) *(optional)*
A small round label that follows the cursor with a spring and changes text
per scene ("SCROLL", "LOOK"). Desktop only. Skip if behind schedule.

## 7. Accessibility and performance

- Wrap the app in `<MotionConfig reducedMotion="user">`. With reduced motion on,
  skip pinned scrubbing: show each scene stacked in normal flow with all
  content visible, and use a simple fade at most.
- Never hide content behind motion. Every scene's text must be readable
  without scrolling effects, and focus order follows reading order.
- Keep text contrast at 4.5:1 or better; red on paper passes for large text only,
  so use ink for small text.
- Budget: 60fps on a mid-range laptop, Lighthouse performance 90 or higher.
  Use `will-change: transform` only on active layers, lazy-load images, and
  prefer CSS shapes over video.
- Mobile: tilt effect off, 12 bars, shorter scroll lengths (about 70%), no
  cursor chip.

## 8. Cut order if time runs short

1. T14 cursor chip
2. T12 route transitions and T13 dashboard micro-motion
3. T11 torn edge, T4 bars (replace with a plain wipe)
4. T3 zoom match cut (replace with T2)

Never cut: T1, T2, T5, T7. They carry the story and the results.

## 9. Open decisions

- 3D hero: CSS 3D transforms first, or a small three.js scene? (Recommended:
  CSS first, upgrade only if there is time.)
- Font licensing: Anton, Inter, and JetBrains Mono are free; confirm before
  switching to any paid font.
- Final name and wordmark treatment for the closing section.
