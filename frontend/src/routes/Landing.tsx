import {
  animate,
  motion,
  type MotionValue,
  useInView,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
} from "motion/react";
import { type ReactNode, useEffect, useRef, useState, useSyncExternalStore } from "react";
import bench from "../lib/benchmark.json";
import { Link } from "../lib/router";
import { springScrub } from "../motion/tokens";

// Real benchmark numbers, written by `make bench-score` (docs/benchmark.md).
const holdout = bench.holdout.setups;
const dev = bench.dev.setups;
const pct = (v: number | null) => (v === null ? "n/a" : `${Math.round(v * 100)}%`);

// Pinned scroll effects only where they help: off with reduced motion and on small screens.
const STILL = "(max-width: 640px), (prefers-reduced-motion: reduce)"; // comma = or

function useStill() {
  return useSyncExternalStore(
    (onChange) => {
      const mq = matchMedia(STILL);
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    },
    () => matchMedia(STILL).matches,
  );
}

type Line = { n: number; kind: "add" | "del" | "ctx"; text: string; marked?: boolean };

const DIFF: Line[] = [
  { n: 1, kind: "del", text: "def average(values):" },
  { n: 2, kind: "del", text: "    return sum(values) / len(values)" },
  { n: 1, kind: "add", text: "def average(values):" },
  { n: 2, kind: "add", text: "    total = 0" },
  { n: 3, kind: "add", text: "    for i in range(1, len(values)):", marked: true },
  { n: 4, kind: "add", text: "        total += values[i]" },
  { n: 5, kind: "add", text: "    return total / len(values)" },
];

function DiffCard({ marked = false }: { marked?: boolean }) {
  return (
    <figure className="diff" style={{ margin: 0 }} aria-label="A pull request changing stats.py">
      <header>stats.py</header>
      <ol>
        {DIFF.map((l, i) => (
          <li key={i} className={l.kind}>
            <span className="n">{l.n}</span>
            <span aria-hidden>{l.kind === "add" ? "+" : l.kind === "del" ? "-" : " "}</span>
            {l.text}
            {marked && l.marked && (
              <motion.i
                className="marker"
                role="img"
                aria-label="Finding on this line"
                initial={{ scale: 0 }}
                whileInView={{ scale: 1 }}
                viewport={{ once: true }}
                transition={{ type: "spring", stiffness: 260, damping: 22 }}
              />
            )}
          </li>
        ))}
      </ol>
    </figure>
  );
}

function Hero() {
  const still = useStill();
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const p = useSpring(scrollYProgress, springScrub);
  const rotateZ = useTransform(p, [0, 0.66], [-16, 0]);
  const rotateY = useTransform(p, [0, 0.66], [-12, 0]);
  const scale = useTransform(p, [0, 0.66], [1.15, 1]);
  const headlineY = useTransform(p, [0, 1], ["0vh", "-40vh"]);

  return (
    <div ref={ref} className={still ? "hero still" : "hero"} style={{ height: still ? "auto" : "150vh" }}>
      <div className="hero-stage" style={{ position: still ? "static" : "sticky" }}>
        <motion.h1 className="hero-title" style={still ? undefined : { y: headlineY }}>
          Every diff, reviewed.
        </motion.h1>
        <motion.div
          className="hero-card"
          style={still ? undefined : { rotateZ, rotateY, scale, transformPerspective: 1200 }}
        >
          <DiffCard marked />
        </motion.div>
        <div className="hero-copy">
          <p>
            DiffMate is a GitHub App that reads each pull request and leaves at most five comments, only where it
            found a real problem. It never changes your code.
          </p>
          <p style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", justifyContent: "center" }}>
            <a className="button" href="#results">
              See how accurate it is
            </a>
            <Link className="button quiet" href="/dashboard">
              Open the dashboard
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

const SCENES: { title: string; body: string; visual: ReactNode; dark?: boolean; red?: boolean }[] = [
  {
    title: "A pull request opens",
    body: "GitHub tells DiffMate a new commit is ready. Forged or replayed notifications are rejected.",
    visual: <DiffCard />,
  },
  {
    title: "It waits its turn",
    body: "Each commit gets one review job. Pushing again queues a new one; the same commit is never reviewed twice.",
    dark: true,
    visual: (
      <ul className="jobs mono">
        <li>stats.py, commit 3f9c2ab: reviewing</li>
        <li>parser.py, commit 81d0e4c: waiting</li>
        <li>api.py, commit c27a913: waiting</li>
      </ul>
    ),
  },
  {
    title: "The AI reads around the change",
    body: "It can open files, search the repository, and find related tests. It cannot run code, write files, or reach the internet.",
    visual: (
      <ol className="trace mono">
        <li>read_file("stats.py")</li>
        <li>search_repo("average(")</li>
        <li>list_related_tests("stats.py")</li>
        <li>submit_findings(1 finding)</li>
      </ol>
    ),
  },
  {
    title: "It marks what is wrong",
    body: "Findings outside the changed lines, below 70% confidence, or repeated are dropped. At most five remain.",
    dark: true,
    visual: <DiffCard marked />,
  },
  {
    title: "A comment lands on the line",
    body: "One review, posted as a comment on the exact line. Plain text only, no links.",
    red: true,
    visual: (
      <div className="comment">
        <strong>Bug, high severity.</strong> The loop starts at 1, so the first value is never added and the average
        comes out too low.
      </div>
    ),
  },
];

function SceneContent({ s, i }: { s: (typeof SCENES)[number]; i: number }) {
  return (
    <div className="scene-grid wrap">
      <div>
        <p className="mono">Step {i + 1} of 5</p>
        <h2>{s.title}</h2>
        <p>{s.body}</p>
      </div>
      <div>{s.visual}</div>
    </div>
  );
}

function WipedScene({ p, i, s }: { p: MotionValue<number>; i: number; s: (typeof SCENES)[number] }) {
  // Scene i slides up over scene i-1 with a hard edge (transform only, DESIGN.md T2).
  const start = (i - 1) / (SCENES.length - 1);
  const y = useTransform(p, [start, start + 0.15], ["100%", "0%"]);
  return (
    <motion.section className={sceneClass(s)} style={i === 0 ? undefined : { y }} aria-label={s.title}>
      <SceneContent s={s} i={i} />
    </motion.section>
  );
}

const sceneClass = (s: (typeof SCENES)[number]) => `scene${s.dark ? " dark" : ""}${s.red ? " red" : ""}`;

function Pipeline() {
  if (useStill())
    return (
      <div data-testid="pipeline-stacked">
        {SCENES.map((s, i) => (
          <section key={s.title} className={`${sceneClass(s)} stacked`} aria-label={s.title}>
            <SceneContent s={s} i={i} />
          </section>
        ))}
      </div>
    );

  return <PinnedPipeline />;
}

// Scroll tracking lives here so it only runs when its target element is rendered.
function PinnedPipeline() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const p = useSpring(scrollYProgress, springScrub);
  return (
    <div ref={ref} style={{ height: `${SCENES.length * 100}vh` }} data-testid="pipeline-pinned">
      <div className="pin">
        {SCENES.map((s, i) => (
          <WipedScene key={s.title} p={p} i={i} s={s} />
        ))}
      </div>
    </div>
  );
}

function Counter({ value, format }: { value: number; format: (v: number) => string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const [shown, setShown] = useState(reduce ? value : 0);

  useEffect(() => {
    if (!inView || reduce) return;
    const controls = animate(0, value, { duration: 1.2, ease: "easeOut", onUpdate: setShown });
    return () => controls.stop();
  }, [inView, reduce, value]);

  return <span ref={ref}>{format(shown)}</span>;
}

function Results() {
  const rows = [
    ["Linters only (ruff, ESLint)", "linter"],
    ["AI only", "agent"],
    ["AI with DiffMate's filters", "filtered"],
  ] as const;
  return (
    <section id="results" className="results wrap">
      <h2>Measured, not promised</h2>
      <p>
        Tested on 60 pull requests from 10 open-source projects (httpx, Flask, Zod, Hono and others), each with a known
        answer. 12 were held back and run once, after all tuning. Model: Gemini Flash Lite on the free tier.
      </p>
      <dl className="stats">
        <div>
          <dt>Comments that were right</dt>
          <dd>
            <Counter value={holdout.filtered.precision ?? 0} format={(v) => `${Math.round(v * 100)}%`} />
          </dd>
        </div>
        <div>
          <dt>Bugs found, held-out set</dt>
          <dd>
            <Counter value={holdout.filtered.recall ?? 0} format={(v) => `${Math.round(v * 100)}%`} />
          </dd>
        </div>
        <div>
          <dt>False alarms per pull request</dt>
          <dd>
            <Counter value={holdout.filtered.fp_per_pr} format={(v) => v.toFixed(2)} />
          </dd>
        </div>
        <div>
          <dt>Cost per review (list price)</dt>
          <dd>
            <Counter value={holdout.filtered.cost_per_pr} format={(v) => `$${v.toFixed(3)}`} />
          </dd>
        </div>
      </dl>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Setup</th>
              <th>Comments that were right</th>
              <th>Bugs found (held-out, 12 PRs)</th>
              <th>Bugs found (tuning set, 48 PRs)</th>
              <th>False alarms per PR</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, key]) => (
              <tr key={key}>
                <td>{label}</td>
                <td>{pct(holdout[key].precision)}</td>
                <td>{pct(holdout[key].recall)}</td>
                <td>{pct(dev[key].recall)}</td>
                <td>{holdout[key].fp_per_pr.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mono">
        It misses more than half of bugs, and says so. When it does comment, it has been right every time so far.
      </p>
    </section>
  );
}

export function Landing() {
  return (
    <>
      <header className="wrap app-bar">
        <span className="brand">DiffMate</span>
        <Link href="/dashboard">Dashboard</Link>
      </header>
      <main>
        <Hero />
        <Pipeline />
        <Results />
        <section className="closing">
          <div className="wrap">
            <h2>Get a second reviewer</h2>
            <p>Install the GitHub App on a repository, then open a pull request.</p>
            <Link className="button" href="/dashboard">
              Open the dashboard
            </Link>
          </div>
        </section>
      </main>
    </>
  );
}
