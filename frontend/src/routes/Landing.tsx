import {
  animate,
  motion,
  type MotionValue,
  useInView,
  useMotionValueEvent,
  useScroll,
  useTransform,
} from "motion/react";
import { useEffect, useId, useRef, useState, useSyncExternalStore } from "react";
import bench from "../lib/benchmark.json";
import logo from "../assets/logo.svg";
import demo from "../lib/demo.json";
import { INSTALL_URL } from "../lib/api";
import { Link } from "../lib/router";

// Live-surface page (scrollcraft/builds/diffmate-landing/BRIEF.md): every comment, step and
// number below is recorded output, from `make bench-score` and `python -m benchmark.demo`.
const holdout = bench.holdout.setups.filtered;
const peak = demo.peak;
const peakComment = peak.comments[0];
const lines = peak.after.replace(/\n$/, "").split("\n");
const totalChars = lines.reduce((n, l) => n + l.length + 1, 0);

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

// Scroll stages of the pinned review act, as fractions of its scroll span.
const TYPE_END = 0.45; // the code is fully written
const TRACE = [0.5, 0.58, 0.66]; // each AI step appears
const SLAM = [0.74, 0.78]; // the red bar crosses the buggy line
const LAND = 0.82; // the comment lands; the rest is a held silence

function Code({ chars, slam, hit }: { chars: number; slam: MotionValue<number> | number; hit: boolean }) {
  let left = chars;
  return (
    <ol className="code" aria-label={`${demo.path}, as written in the pull request`}>
      {lines.map((text, i) => {
        const shown = text.slice(0, Math.max(0, left));
        const visible = left > 0;
        left -= text.length + 1;
        const bug = i + 1 === peakComment.line;
        return (
          <li key={i} className={bug ? `bug-line${hit ? " hit" : ""}` : undefined} style={{ visibility: visible ? "visible" : "hidden" }}>
            {bug && <motion.i className="slam" aria-hidden style={{ scaleX: slam }} />}
            <span className="n">{i + 1}</span>
            <span className="t">{shown || " "}</span>
          </li>
        );
      })}
    </ol>
  );
}

function Comment() {
  return (
    <aside className="review-comment" aria-label="DiffMate's comment">
      <p className="mono">
        diffmate[bot] on line {peakComment.line}: {peakComment.category}, {peakComment.severity}
      </p>
      <p>{peakComment.explanation}</p>
    </aside>
  );
}

function Trace({ shown }: { shown: number }) {
  return (
    <ol className="trace mono" aria-label="What the AI did">
      {peak.trace.map((s, i) => (
        <li key={s} style={{ opacity: i < shown ? 1 : 0 }}>
          {s}
        </li>
      ))}
    </ol>
  );
}

function ReviewStill() {
  return (
    <section className="act review" aria-label="The review" data-testid="review-still">
      <div className="surface">
        <Code chars={totalChars} slam={1} hit />
        <div className="side">
          <Trace shown={peak.trace.length} />
          <Comment />
        </div>
      </div>
    </section>
  );
}

// Signature move: the visitor's scroll writes the pull request, then DiffMate reviews it.
function ReviewPinned() {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress: p } = useScroll({ target: ref, offset: ["start start", "end end"] });
  const [progress, setProgress] = useState(0);
  useMotionValueEvent(p, "change", setProgress);
  const slam = useTransform(p, SLAM, [0, 1]);

  // Start with line 1 written so the box never looks empty.
  const chars = Math.max(lines[0].length, Math.round(Math.min(progress / TYPE_END, 1) * totalChars));
  const stepsShown = TRACE.filter((at) => progress >= at).length;
  const status =
    progress < 0.03
      ? "scroll down: the code writes itself, then DiffMate reviews it"
      : progress < TYPE_END
        ? "being written"
        : progress < SLAM[0]
          ? "DiffMate is reviewing"
          : "1 comment from DiffMate";
  const landed = progress >= LAND;

  return (
    <div ref={ref} className="review-track" data-testid="review-pinned">
      <section className="act review pin" aria-label="The review">
        <p className="statusline mono">
          {demo.path}, {status}
        </p>
        <div className="surface">
          <Code chars={chars} slam={slam} hit={progress >= SLAM[1]} />
          <div className="side">
            <Trace shown={stepsShown} />
            {landed && (
              <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.18 }}>
                <Comment />
              </motion.div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function Count({ value, format }: { value: number; format: (v: number) => string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const still = useStill();
  const [shown, setShown] = useState(still ? value : 0);

  useEffect(() => {
    if (still) return setShown(value);
    if (!inView) return;
    const controls = animate(0, value, { duration: 1.2, ease: "easeOut", onUpdate: setShown });
    return () => controls.stop();
  }, [inView, still, value]);

  return <span ref={ref}>{format(shown)}</span>;
}

const pct = (v: number) => `${Math.round(v * 100)}%`;

function Numbers() {
  return (
    <section id="numbers" className="act numbers" aria-label="How accurate it is">
      <p className="mono">Benchmark: {bench.holdout.cases} held-out pull requests, run once</p>
      <dl>
        <div>
          <dd>
            <Count value={holdout.precision ?? 0} format={pct} />
          </dd>
          <dt>of its comments were right</dt>
        </div>
        <div>
          <dd>
            <Count value={holdout.recall ?? 0} format={pct} />
          </dd>
          <dt>of the bugs it found. It misses most, and says so.</dt>
        </div>
        <div>
          <dd>
            <Count value={holdout.fp_per_pr} format={(v) => v.toFixed(2)} />
          </dd>
          <dt>false alarms per pull request</dt>
        </div>
      </dl>
      <p className="note">
        60 pull requests from 10 open-source projects (httpx, Flask, Zod, Hono and others), each with a known answer. On
        the 48 cases used for tuning it found {pct(bench.dev.setups.filtered.recall ?? 0)} of the bugs; linters alone
        found {pct(bench.dev.setups.linter.recall ?? 0)}. Model: Gemini Flash Lite on the free tier, estimated $
        {holdout.cost_per_pr.toFixed(3)} per review at list price.
      </p>
    </section>
  );
}

const BREAK_LABELS: Record<string, string> = {
  loop: "Start the loop at 1",
  slice: "Take the last n items with items[-n:]",
  shell: "Run tar through the shell",
};

type BreakKey = keyof typeof demo.breaks;

function PlantABug() {
  const [choice, setChoice] = useState<BreakKey | null>(null);
  const name = useId();
  const run = choice ? demo.breaks[choice] : null;
  const clean = demo.clean.replace(/\n$/, "").split("\n");
  const after = run ? run.after.replace(/\n$/, "").split("\n") : clean;

  return (
    <section id="try" className="act plant" aria-label="Plant a bug">
      <h2>Break one line. See what DiffMate said.</h2>
      <fieldset>
        <legend className="mono">Your change to {demo.path}</legend>
        {(Object.keys(demo.breaks) as BreakKey[]).map((key) => (
          <label key={key}>
            <input type="radio" name={name} value={key} checked={choice === key} onChange={() => setChoice(key)} />
            {BREAK_LABELS[key] ?? key}
          </label>
        ))}
      </fieldset>
      <div className="surface">
        <ol className="code small" aria-label={`${demo.path}, with your change`}>
          {after.map((text, i) => (
            <li key={i} className={run && text !== clean[i] ? "changed" : undefined}>
              <span className="n">{i + 1}</span>
              <span className="t">{text || " "}</span>
            </li>
          ))}
        </ol>
        <div className="side" aria-live="polite">
          {!run && <p>Pick a change. Each one was reviewed by the real DiffMate.</p>}
          {run && run.comments.length === 0 && <p>DiffMate posted nothing for this change.</p>}
          {run?.comments.map((c) => (
            <aside className="review-comment" key={c.line}>
              <p className="mono">
                diffmate[bot] on line {c.line}: {c.category}, {c.severity}
              </p>
              <p>{c.explanation}</p>
            </aside>
          ))}
          {run && (
            <p className="mono note">
              Recorded {demo.recorded} with {demo.model}, {run.llm_requests} AI requests. Not live.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

export function Landing() {
  const still = useStill();
  return (
    <>
      <nav className="chrome" aria-label="Page">
        <span className="wordmark">
          <img src={logo} alt="" width={22} height={22} />
          DiffMate
        </span>
        <a href="#review">Review</a>
        <a href="#numbers">Numbers</a>
        <a href="#try">Try it</a>
        <Link href="/dashboard" className="right">
          Dashboard
        </Link>
      </nav>
      <main>
        <header className="act hook">
          <h1>DiffMate reviews your pull requests and comments only where it finds a bug.</h1>
          <div className="pr-head">
            <p className="mono">Pull request #12, {demo.path}</p>
            <p className="pr-title">Add stats helpers</p>
            <p className="mono">Review requested from diffmate[bot]. Waiting.</p>
          </div>
        </header>
        <div id="review">{still ? <ReviewStill /> : <ReviewPinned />}</div>
        <Numbers />
        <PlantABug />
        <footer className="act close">
          <p>
            <a className="button" href={INSTALL_URL}>
              Install on GitHub
            </a>
          </p>
          <p>
            Pick your repositories, open a pull request, and the review appears there within a minute or two. Public
            repositories only: DiffMate uses a free AI service that may learn from the code it reads.{" "}
            <Link href="/dashboard">Open the dashboard</Link>
          </p>
        </footer>
      </main>
    </>
  );
}
