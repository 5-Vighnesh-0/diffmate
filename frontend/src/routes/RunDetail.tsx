import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { Shell } from "../components/ui/Shell";
import {
  api,
  type FeedbackSummary,
  type Finding,
  type Me,
  post,
  type Run,
  type TraceStep,
  usefulLine,
  type Verdict,
} from "../lib/api";
import { Link } from "../lib/router";

type Detail = Omit<Run, "findings"> & { findings: Finding[] };

// Plain-language labels for people new to code review.
const WHERE: Record<string, string> = {
  posted: "Sent to GitHub, where the person who made the change can see it.",
  dropped_not_in_diff: "Not sent to GitHub: it is about code this change did not touch.",
  dropped_low_confidence: "Not sent to GitHub: DiffMate was not sure enough.",
  dropped_duplicate: "Not sent to GitHub: another note already says the same thing.",
  dropped_over_cap: "Not sent to GitHub: DiffMate sends at most 5 notes per review.",
  dropped_stricter:
    "Not sent to GitHub: people on this repo marked most notes of this kind not useful, so DiffMate needs to be surer.",
};
export const KIND: Record<string, string> = { bug: "Mistake", security: "Security risk", missing_test: "Missing test" };
const IMPORTANCE: Record<string, string> = { high: "serious", medium: "worth fixing", low: "minor" };
const STEP: Record<string, string> = {
  read_file: "Opened a file to read it",
  search_repo: "Searched the project",
  view_diff_hunk: "Looked closely at part of the change",
  list_related_tests: "Looked for the project's tests",
  submit_findings: "Wrote its notes",
};

export function RunDetail({ id }: { id: number }) {
  return <Shell>{(me) => <Review id={id} me={me} />}</Shell>;
}

function Review({ id, me }: { id: number; me: Me }) {
  const [run, setRun] = useState<Detail | null>(null);
  const [trace, setTrace] = useState<TraceStep[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [voteError, setVoteError] = useState<string | null>(null);
  const [saved, setSaved] = useState<number | null>(null); // finding id whose vote just saved
  const [score, setScore] = useState<string | null>(null); // the user's running "useful" score

  useEffect(() => {
    Promise.all([api<Detail>(`/api/runs/${id}`), api<TraceStep[]>(`/api/runs/${id}/trace`)])
      .then(([r, t]) => {
        setRun(r);
        setTrace(t);
      })
      .catch((e) => setError(e.status === 404 ? "This review does not exist or is not yours." : e.message));
  }, [id]);

  async function vote(f: Finding, verdict: Verdict) {
    try {
      await post(`/api/findings/${f.id}/feedback`, me.csrf_token, { verdict });
    } catch (e) {
      setVoteError(`Your vote was not saved: ${(e as Error).message}`);
      return;
    }
    setVoteError(null);
    setSaved(f.id);
    api<FeedbackSummary>("/api/feedback/summary")
      .then((s) => setScore(usefulLine(s)))
      .catch(() => setScore(null));
    setRun((r) => r && { ...r, findings: r.findings.map((x) => (x.id === f.id ? { ...x, my_verdict: verdict } : x)) });
  }

  if (error) return <p className="notice" role="alert">{error}</p>;
  if (!run) return <p>Loading review…</p>;

  const rated = run.findings.filter((f) => f.my_verdict).length;
  const n = run.findings.length;
  const posted = run.findings.filter((f) => f.status === "posted").length;
  const prUrl = `https://github.com/${run.repo}/pull/${run.pr}`;

  // real time since the AI started: each step ends when its AI answer came back
  let total = 0;
  const elapsed = trace.map((s) => (total += s.duration_ms));

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <p>
        <Link href="/dashboard">All reviews</Link>
      </p>
      <h1 style={{ fontSize: "3rem" }}>"{run.title}"</h1>
      <p>
        DiffMate's review of change #{run.pr} in {run.repo}, checked {new Date(run.created_at).toLocaleString()}.{" "}
        <a href={prUrl} target="_blank" rel="noreferrer">
          See the change on GitHub
        </a>
      </p>
      <p className="mono fine">
        Version {run.commit_sha.slice(0, 7)} of the change. The AI was asked {run.llm_requests} times. Cost: $0 (free
        tier; about ${run.est_cost_usd.toFixed(4)} at paid prices).
      </p>
      {run.error && <p className="notice" role="alert">{run.error}</p>}

      <section className="intro">
        <h2>What DiffMate noticed</h2>
        {n === 0 && run.error ? (
          <p>DiffMate did not finish reading this change, so having no notes here does not mean it is fine.</p>
        ) : n === 0 ? (
          <p>DiffMate read this change and found nothing worth a note. That is a good sign, though not a guarantee.</p>
        ) : (
          <p>
            DiffMate noticed {n} possible {n === 1 ? "problem" : "problems"}. It sent {posted} to GitHub as{" "}
            {posted === 1 ? "a note" : "notes"} on the exact line; {n - posted === 0 ? "none were" : `${n - posted} ${n - posted === 1 ? "was" : "were"}`}{" "}
            held back, and each one says why.
          </p>
        )}
        {n > 0 && (
          <p>
            <strong>Was each note right?</strong> Choose <em>Useful</em> if it points at a real problem, or{" "}
            <em>Not useful</em> if it is wrong or unimportant. Your answer is saved only in DiffMate, never on GitHub, and
            is used to measure how often DiffMate is right. You can change it any time.
          </p>
        )}
      </section>
      {voteError && <p className="notice" role="alert">{voteError}</p>}
      {run.findings.length > 0 && (
        <p className="mono" aria-live="polite">
          You have rated {rated} of {n}.
        </p>
      )}
      {run.findings.map((f, i) => (
        <motion.article
          className="finding"
          key={f.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 + i * 0.06, duration: 0.25 }}
        >
          <p className="meta">
            <strong>{KIND[f.category] ?? f.category}</strong>, {IMPORTANCE[f.severity] ?? f.severity}. In{" "}
            <code>{f.file}</code>, line {f.line}. DiffMate is {Math.round(f.confidence * 100)}% sure.
          </p>
          <p className="fine">{WHERE[f.status] ?? f.status}</p>
          {/* LLM text: React renders it as text, never HTML. */}
          <p>{f.explanation}</p>
          <div className="actions" role="group" aria-label="Was this comment useful?">
            <motion.button
              whileTap={{ scale: 0.96 }}
              className="button quiet"
              aria-pressed={f.my_verdict === "accept"}
              onClick={() => vote(f, "accept")}
            >
              Useful
            </motion.button>
            <motion.button
              whileTap={{ scale: 0.96 }}
              className="button quiet"
              aria-pressed={f.my_verdict === "reject"}
              onClick={() => vote(f, "reject")}
            >
              Not useful
            </motion.button>
            <AnimatePresence>
              {saved === f.id && (
                <motion.span
                  className="saved mono"
                  role="status"
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  Saved: {f.my_verdict === "accept" ? "useful" : "not useful"}.
                  {score && ` So far you've found ${score}.`}
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </motion.article>
      ))}

      <section className="intro">
        <h2>How DiffMate checked it</h2>
        <p>
          Every step it took, with the real time since the AI started (each AI answer is timed). It can only read code,
          never change it.
        </p>
      </section>
      {trace.length === 0 ? (
        <p>No steps recorded.</p>
      ) : (
        <section className="rail run-rail" aria-label="Timeline of this review">
          <ol>
            {trace.map((s, i) => (
              <motion.li
                key={s.step_no + s.summary}
                className="on"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + i * 0.04 }}
              >
                <span className="t">+{(elapsed[i] / 1000).toFixed(1)} s</span>
                <span className="x plain">{STEP[s.tool] ?? s.tool}</span>
                <span className="fine">{s.summary}</span>
              </motion.li>
            ))}
          </ol>
        </section>
      )}

      <section className="intro next">
        <h2>What next?</h2>
        <p>
          If a note is right, fix that line and update the change on GitHub. DiffMate checks every new version
          automatically, and the new review appears in <Link href="/dashboard">your reviews</Link>.
        </p>
      </section>
    </motion.div>
  );
}
