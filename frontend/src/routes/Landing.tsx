import { animate, useInView } from "motion/react";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import logo from "../assets/logo.svg";
import { ReviewFlow } from "../components/ReviewFlow";
import bench from "../lib/benchmark.json";
import { INSTALL_URL } from "../lib/api";
import { Link } from "../lib/router";

// Live-surface page (scrollcraft/builds/diffmate-landing/BRIEF.md): every comment, step and
// number below is recorded output, from `make bench-score` and `python -m benchmark.demo`.
const holdout = bench.holdout.setups.filtered;

const STILL = "(prefers-reduced-motion: reduce)";

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
      <p className="mono">Benchmark: {bench.holdout.cases} held-out pull requests, kept out of all tuning</p>
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
          <dt>of the bugs it found. It still misses some, and says so.</dt>
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

export function Landing() {
  const still = useStill();
  return (
    <>
      <nav className="chrome" aria-label="Page">
        <span className="wordmark">
          <img src={logo} alt="" width={22} height={22} />
          DiffMate
        </span>
        <a href="#review">How it works</a>
        <a href="#numbers">Numbers</a>
        <Link href="/dashboard" className="right">
          Dashboard
        </Link>
      </nav>
      <main>
        <header className="act hook">
          <h1>DiffMate reviews your pull requests and comments only where it finds a bug.</h1>
        </header>
        <div id="review">
          <ReviewFlow still={still} />
        </div>
        <Numbers />
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
