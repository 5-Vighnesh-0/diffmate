import { useMotionValueEvent, useScroll } from "motion/react";
import { type ReactNode, useMemo, useRef, useState } from "react";
import demo from "../lib/demo.json";
import { changeOf, INTRO, playAt, realAt, timeline, type Step, type Timeline } from "../lib/flow";

// Scroll flow: the visitor's scroll moves one recorded pull request through DiffMate.
// Left, every event with its time; middle, GitHub; right, inside DiffMate.
const EXAMPLES = [
  { key: "loop", label: "The loop starts at 1", title: "Use an index in average" },
  { key: "slice", label: "Last n items", title: "Shorten last_n with a slice" },
  { key: "shell", label: "tar through a shell", title: "Simplify archive" },
] as const;

const WHY: Record<string, string> = {
  view_diff_hunk: "Looks at the changed lines again, closely.",
  read_file: "Reads the file around the change to understand the whole function.",
  list_related_tests: "Checks whether any tests cover this file.",
  search_repo: "Searches the repo for other places that use this code.",
  submit_findings: "Hands back its notes. This ends the AI's turn.",
};

const VH_PER_SECOND = 26; // scroll length per second of flow
const clamp = (x: number) => Math.min(1, Math.max(0, x));
const between = (x: number, a: number, b: number) => clamp((x - a) / (b - a));
const stamp = (s: number) => `${s < 0 ? "−" : "+"}${Math.abs(s).toFixed(2)} s`;

function captions(tl: Timeline): [number, string][] {
  return [
    [0, "A developer edits stats.py. Red lines are removed, green lines added. It looks fine."],
    [INTRO - 0.6, "They open a pull request. DiffMate is installed on this repo, so the clock starts."],
    [INTRO, "GitHub sends DiffMate a signed message. A fake one is rejected, and private repos are ignored."],
    [INTRO + 0.9, "DiffMate downloads only the changed lines, not the whole project, and runs the linters first."],
    [tl.aiFrom, "The AI investigates with read-only tools. Most of this time is spent waiting for its answers."],
    [tl.hit - 0.95, "It found one problem. Before anything is posted, a filter checks the note."],
    [tl.hit, `Caught. One comment on the exact line, ${tl.seconds} seconds after the pull request opened.`],
    [tl.hit + 0.6, "The developer votes. Over time DiffMate learns which notes this repo finds useful."],
  ];
}

const latest = <T,>(items: [number, T][], t: number) => [...items].reverse().find(([at]) => t >= at)?.[1] ?? items[0][1];

function StepIcon() {
  return (
    <svg className="ic" viewBox="0 0 18 18" aria-hidden="true">
      <circle className="todo" cx="9" cy="9" r="7" fill="none" strokeWidth="2" />
      <g className="done">
        <circle cx="9" cy="9" r="8" />
        <path d="M5 9.2l2.6 2.6L13 6.4" fill="none" stroke="#0a0a0a" strokeWidth="2.2" />
      </g>
    </svg>
  );
}

// Owns the scroll tracking, so the still (reduced-motion) layout never needs a scroll target.
function ScrollTrack({ height, onProgress, children }: { height: string; onProgress: (p: number) => void; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end end"] });
  useMotionValueEvent(scrollYProgress, "change", onProgress);
  return (
    <div ref={ref} className="flow-track" style={{ height }}>
      {children}
    </div>
  );
}

export function ReviewFlow({ still }: { still: boolean }) {
  const [pick, setPick] = useState(0);
  const ex = EXAMPLES[pick];
  const run = demo.breaks[ex.key];
  const tl = useMemo(() => timeline(run, demo.clean), [run]);
  const change = useMemo(() => changeOf(demo.clean, run.after), [run]);

  const section = useRef<HTMLElement>(null);
  const [progress, setProgress] = useState(0);

  const v = still ? tl.duration : progress * tl.duration;
  const t = realAt(tl, v);
  const c = run.comments[0];

  function choose(i: number) {
    setPick(i);
    if (!still) section.current?.querySelector(".flow-track")?.scrollIntoView({ behavior: "smooth" });
  }

  // The visitor's change types itself in, then the pull request opens.
  let typed = Math.round(between(t, 1, INTRO - 1.2) * change.added.join("").length);
  const shown = new Map<number, string>();
  change.lines.forEach((l, i) => {
    if (l.kind !== "add") return;
    shown.set(i, l.text.slice(0, Math.max(0, typed)));
    typed -= l.text.length;
  });
  const anchor = change.lines.findIndex((l) => l.kind !== "same");
  const opened = t >= INTRO - 0.4;
  const status = t < 1 ? "Your branch: you/stats-change" : !opened ? "Ready to open" : t < tl.hit ? "Waiting for review" : "Reviewed by diffmate[bot]";

  // The AI's requests, spread evenly inside the recorded total (estimated).
  const inAi = t >= tl.aiFrom && t < tl.aiTo;
  const aiStep = Math.floor((t - tl.aiFrom) / tl.per);
  const reading = inAi && /read_file|view_diff/.test(run.trace[aiStep] ?? "");

  // The catch: the scroll holds still while red wipes across the line and the header.
  const catchAt = playAt(tl, tl.hit);
  const wipe = `inset(0 ${(1 - between(v, catchAt, catchAt + 0.5)) * 100}% 0 0)`;
  const landed = between(v, catchAt + 0.6, catchAt + 1.1);

  const out = between(t, INTRO, INTRO + 0.9);
  const back = between(t, tl.hit - 0.5, tl.hit);
  const done = (step: Step) => tl.events.find((e) => e.step === step)!;
  const current = [...tl.events].reverse().find((e) => e.step && t >= e.at)?.step;
  const due = tl.events.filter((e) => t >= e.at);
  const side = t >= tl.hit || !due.length ? "github" : due[due.length - 1].side;
  const percent = Math.round(c.confidence * 100);

  // a plain function, not a component, so rows are not remounted on every scroll frame
  function row(step: Step, title: string, children?: ReactNode) {
    const e = done(step);
    const on = t >= e.at;
    return (
      <div className={`row${on ? " on" : ""}${current === step && t < tl.hit + 0.3 ? " cur" : ""}`}>
        <div className="row-h">
          <StepIcon />
          <div>
            <b>{title}</b>
            {children}
          </div>
          <span className="ts">{on ? stamp(e.at - INTRO) : ""}</span>
        </div>
      </div>
    );
  }

  const stage = (
    <div className="stage">
      <div className="now" aria-live="polite">
        <span className="chap">{latest(tl.chapters, t)}</span>
        <p>{latest(captions(tl), t)}</p>
        {inAi && !still && <span className="ff">Fast-forward: waiting for the AI</span>}
        <i className="band" aria-hidden style={{ clipPath: wipe }} />
      </div>
      <div className="cols" data-side={still ? "both" : side}>
        <section className="rail" aria-labelledby="rail-h">
          <h3 id="rail-h">
            Timeline <small>since "Create pull request"</small>
          </h3>
          <ol>
            {tl.events.map((e, i) => {
              const on = t >= e.at;
              const last = on && (i === tl.events.length - 1 || t < tl.events[i + 1].at);
              return (
                <li key={i} className={`${on ? "on" : ""}${last ? " cur" : ""}${e.key ? " key" : ""}`}>
                  <span className="t">
                    {stamp(e.at - INTRO)} <span className="who">{e.who}</span>
                  </span>
                  <span className="x">{e.text}</span>
                </li>
              );
            })}
          </ol>
        </section>

        <section className="ghlane" aria-labelledby="gh-h">
          <h3 id="gh-h">
            On GitHub <small>what you see</small>
          </h3>
          <div className="gh">
            <div className="gh-top">
              <div className="gh-title">
                {ex.title} <span>#12</span>
              </div>
              <span className="createbtn" aria-hidden style={{ opacity: opened ? 0 : 1 }}>
                Create pull request
              </span>
              <span className={`pill${opened ? " open" : ""}`}>{opened ? "Open, review requested from diffmate[bot]" : "Draft"}</span>
              <div className="status">{status}</div>
            </div>
            <ol className="flow-code" aria-label={`${demo.path}, as changed in the pull request`}>
              {reading && (
                <i className="reader" aria-hidden style={{ transform: `translateY(${(((t - tl.aiFrom) / tl.per) % 1) * 11}lh)` }} />
              )}
              {change.lines.map((l, i) => {
                if (Math.abs(i - anchor) > 5) return null;
                const hidden = l.kind !== "same" && t < 1;
                const text = l.kind === "add" ? shown.get(i)! : l.text;
                const outlined = l.kind === "add" && t >= INTRO + 0.9 && t < tl.hit;
                return (
                  <li key={i} className={l.kind} style={{ visibility: hidden ? "hidden" : "visible" }}>
                    {l.kind === "add" && l.n === c.line && <i className="slam" aria-hidden style={{ clipPath: wipe }} />}
                    <span className="n">{l.n ?? ""}</span>
                    <span>{l.kind === "add" ? "+" : l.kind === "del" ? "-" : " "}</span>
                    <span className="t">{text || " "}</span>
                    {outlined && <i className="hl" aria-hidden />}
                  </li>
                );
              })}
            </ol>
            {landed > 0 && (
              <div className="flow-comment" style={{ opacity: landed, transform: `translateY(${(1 - landed) * 12}px)` }}>
                <div className="who">
                  diffmate[bot] commented on line {c.line}{" "}
                  <em>
                    {c.category}, {c.severity}
                  </em>
                </div>
                <p>{c.explanation}</p>
                <div className="votes" aria-hidden>
                  <span>Useful</span>
                  <span>Not useful</span>
                </div>
              </div>
            )}
          </div>
        </section>

        <div className="wire" aria-hidden>
          <span className="wire-label">signed webhook over HTTPS</span>
          {out > 0 && out < 1 && (
            <div className="msg out" style={{ transform: `translateX(${(out - 0.5) * 250}px)` }}>
              POST /webhooks/github
              <br />
              pull_request.opened
            </div>
          )}
          {back > 0 && back < 1 && (
            <div className="msg back" style={{ transform: `translateX(${(0.5 - back) * 250}px)` }}>
              1 comment for line {c.line}
            </div>
          )}
        </div>

        <section className="dmlane" aria-labelledby="dm-h">
          <h3 id="dm-h">
            Inside DiffMate <small>what happens meanwhile</small>
          </h3>
          <div className="dm">
            {row(
              "verify",
              "Checks the message",
              <span className="d">Is the signature genuine, is the repo public, is this a repeat? Then the job is queued.</span>,
            )}
            {row(
              "diff",
              "Reads only what changed",
              <span className="d">
                Fetches the {change.added.length} changed line{change.added.length === 1 ? "" : "s"}, not your whole project, and
                runs the linters first.
              </span>,
            )}
            {row(
              "ai",
              "The AI investigates",
              <>
                <span className="d">Read-only tools, at most 8 steps. It cannot run code, reach the internet or change your repo.</span>
                <ol className="calls">
                {run.trace.map((call, j) => {
                  const at = tl.aiFrom + j * tl.per;
                  return (
                    <li key={j} className={`${t >= at ? "on" : ""}${t >= at && t < at + tl.per ? " cur" : ""}`}>
                      <code>{call}</code>
                      <span className="why">{WHY[call.split("(")[0]] ?? ""}</span>
                    </li>
                  );
                })}
                </ol>
              </>,
            )}
            {row(
              "filter",
              "Keeps only sure notes",
              t >= tl.hit - 0.95 && (
                <div className="note-card">
                  <div className="h">
                    A {c.category} on line {c.line}, {percent}% sure
                  </div>
                  <div className="bar">
                    <i style={{ transform: `scaleX(${between(t, tl.hit - 0.95, tl.hit - 0.7) * c.confidence})` }} />
                  </div>
                  <ul>
                    <li>On a line this pull request changed</li>
                    <li>{percent}% sure; it needs at least 70%</li>
                    <li>1 note, under the limit of 5</li>
                  </ul>
                </div>
              ),
            )}
            {row("post", "Posts the comment", <span className="d">One review on GitHub, inline on the exact line.</span>)}
            <div className="big">
              <div>
                <div className={`n${t >= tl.hit ? " locked" : ""}`}>{(between(t, INTRO, tl.hit) * tl.seconds).toFixed(1)} s</div>
                <div className="l">since the PR opened (real)</div>
              </div>
              <div>
                <div className="n">{t >= tl.hit ? run.llm_requests : t >= tl.aiFrom ? Math.min(run.llm_requests, aiStep + 1) : 0}</div>
                <div className="l">AI requests, free tier</div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );

  return (
    <section ref={section} className="flow" aria-labelledby="flow-h" data-testid={still ? "flow-still" : "flow-pinned"}>
      <div className="flow-intro">
        <h2 id="flow-h">
          You wait a minute.
          <br />
          Here is that minute.
        </h2>
        <p className="lead">
          {still ? "One" : "Scroll, and one"} real pull request flows through DiffMate. Every event, with its time, from "Create
          pull request" to the comment.
        </p>
        <div className="picker" role="group" aria-label="Choose a recorded pull request">
          {EXAMPLES.map((e, i) => (
            <button key={e.key} type="button" aria-pressed={i === pick} onClick={() => choose(i)}>
              {e.label}
            </button>
          ))}
        </div>
      </div>
      {still ? (
        stage
      ) : (
        <ScrollTrack height={`calc(${Math.round(tl.duration * VH_PER_SECOND)}vh + 100vh)`} onProgress={setProgress}>
          {stage}
        </ScrollTrack>
      )}
      <p className="flow-honest">
        Real, recorded {demo.recorded} with {demo.model}: the change, the comment, the order of the AI's {run.llm_requests}{" "}
        requests and the total of {tl.seconds} s. Estimated: when each AI request happened inside that total. The AI's waiting
        takes less scroll than it took in real life; the clock shows real seconds.
      </p>
    </section>
  );
}
