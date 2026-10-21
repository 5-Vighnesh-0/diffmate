import { motion } from "motion/react";
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
    setRun((r) => r && { ...r, findings: r.findings.map((x) => (x.id === f.id ? { ...x, my_verdict: verdict } : x)) });
  }

  if (error) return <p className="notice" role="alert">{error}</p>;
  if (!run) return <p>Loading review…</p>;

  return (
    <>
      <p>
        <Link href="/dashboard">All reviews</Link>
      </p>
      <h1 style={{ fontSize: "3rem" }}>
        {run.repo} #{run.pr}
      </h1>
      <p>{run.title}</p>
      <p className="mono">
        Commit {run.commit_sha.slice(0, 7)}, {run.llm_requests} AI requests, estimated ${run.est_cost_usd.toFixed(4)} at
        list price (free tier: $0)
      </p>
      {run.error && <p className="notice" role="alert">{run.error}</p>}

      <h2 style={{ fontSize: "2rem", margin: "2rem 0 1rem" }}>Comments</h2>
      {voteError && <p className="notice" role="alert">{voteError}</p>}
      {run.findings.length === 0 && <p>DiffMate found nothing worth a comment in this pull request.</p>}
      {run.findings.map((f) => (
        <article className="finding" key={f.id}>
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
          </div>
        </article>
      ))}

      <h2 style={{ fontSize: "2rem", margin: "2rem 0 1rem" }}>What the AI did</h2>
      {trace.length === 0 ? (
        <p>No steps recorded.</p>
      ) : (
        <ol className="mono" style={{ paddingLeft: "1.5rem" }}>
          {trace.map((s, i) => (
            <motion.li
              key={s.step_no + s.summary}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              style={{ marginBottom: "0.5rem", overflowWrap: "anywhere" }}
            >
              {s.summary}
              {s.duration_ms > 0 && ` (${(s.duration_ms / 1000).toFixed(1)} s)`}
            </motion.li>
          ))}
        </ol>
      )}
    </>
  );
}
