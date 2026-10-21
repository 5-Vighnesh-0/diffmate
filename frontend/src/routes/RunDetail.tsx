import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { Shell } from "../components/ui/Shell";
import { api, type Finding, type Me, post, type Run, type TraceStep, type Verdict } from "../lib/api";
import { Link } from "../lib/router";

type Detail = Omit<Run, "findings"> & { findings: Finding[] };

const DROPPED: Record<string, string> = {
  posted: "Posted on GitHub",
  dropped_not_in_diff: "Not posted: outside the changed lines",
  dropped_low_confidence: "Not posted: low confidence",
  dropped_duplicate: "Not posted: duplicate",
  dropped_over_cap: "Not posted: over the 5-comment limit",
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
    setRun((r) => r && { ...r, findings: r.findings.map((x) => (x.id === f.id ? { ...x, my_verdict: verdict } : x)) });
  }

  if (error) return <p className="notice" role="alert">{error}</p>;
  if (!run) return <p>Loading review…</p>;

  const rated = run.findings.filter((f) => f.my_verdict).length;
  const posted = run.findings.filter((f) => f.status === "posted").length;
  const prUrl = `https://github.com/${run.repo}/pull/${run.pr}`;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <p>
        <Link href="/dashboard">All reviews</Link>
      </p>
      <h1 style={{ fontSize: "3rem" }}>
        {run.repo} #{run.pr}
      </h1>
      <p>
        {run.title}.{" "}
        <a href={prUrl} target="_blank" rel="noreferrer">
          Open the pull request on GitHub
        </a>
      </p>
      <p className="mono">
        Commit {run.commit_sha.slice(0, 7)}, {run.llm_requests} AI requests, estimated ${run.est_cost_usd.toFixed(4)} at
        list price (free tier: $0)
      </p>
      {run.error && <p className="notice" role="alert">{run.error}</p>}

      <section className="intro">
        <h2>Comments</h2>
        <p>
          DiffMate found {run.findings.length} possible {run.findings.length === 1 ? "problem" : "problems"} in this
          commit and posted {posted} of them as comments on the pull request. The rest were held back by its filters
          (each says why), so they never reached GitHub.
        </p>
        {run.findings.length > 0 && (
          <p>
            <strong>Was each comment right?</strong> Choose <em>Useful</em> if it points at a real problem, or{" "}
            <em>Not useful</em> if it is wrong or noise. Your answer is saved only in DiffMate, never on GitHub, and is
            used to measure how often DiffMate is right. You can change it any time.
          </p>
        )}
      </section>
      {voteError && <p className="notice" role="alert">{voteError}</p>}
      {run.findings.length > 0 && (
        <p className="mono" aria-live="polite">
          You have rated {rated} of {run.findings.length}.
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
          <p className="meta mono">
            {f.file}:{f.line}, {f.category}, {f.severity} severity, {Math.round(f.confidence * 100)}% confident.{" "}
            {DROPPED[f.status] ?? f.status}
          </p>
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
                  Saved: {f.my_verdict === "accept" ? "useful" : "not useful"}
                </motion.span>
              )}
            </AnimatePresence>
          </div>
        </motion.article>
      ))}

      <section className="intro">
        <h2>What the AI did</h2>
        <p>Every step DiffMate took before commenting, in order. It can only read your code, never change it.</p>
      </section>
      {trace.length === 0 ? (
        <p>No steps recorded.</p>
      ) : (
        <ol className="mono" style={{ paddingLeft: "1.5rem" }}>
          {trace.map((s, i) => (
            <motion.li
              key={s.step_no + s.summary}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 + i * 0.04 }}
              style={{ marginBottom: "0.5rem", overflowWrap: "anywhere" }}
            >
              {s.summary}
              {s.duration_ms > 0 && ` (${(s.duration_ms / 1000).toFixed(1)} s)`}
            </motion.li>
          ))}
        </ol>
      )}

      <section className="intro next">
        <h2>What next?</h2>
        <p>
          Fix the code on GitHub and push. DiffMate reviews every new commit automatically, and the new review appears
          in <Link href="/dashboard">your reviews</Link>.
        </p>
      </section>
    </motion.div>
  );
}
