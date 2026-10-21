import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { Shell } from "../components/ui/Shell";
import { api, type Run } from "../lib/api";
import { Link } from "../lib/router";

const STATUS: Record<Run["status"], { label: string; help: string }> = {
  queued: { label: "Waiting", help: "in line; reviews run one at a time" },
  running: { label: "Reviewing", help: "the AI is reading the change right now" },
  done: { label: "Done", help: "the review is posted on GitHub" },
  failed: { label: "Failed", help: "something went wrong; open it to see why" },
  paused_daily_cap: {
    label: "Paused",
    help: "the free daily AI limit was reached; it continues after the limit resets",
  },
};

export function Dashboard() {
  return <Shell>{() => <Runs />}</Shell>;
}

function Intro() {
  return (
    <motion.section
      className="intro"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
    >
      <h1>Your reviews</h1>
      <p>
        Each time a pull request is opened or updated in a repository where DiffMate is installed, it reviews the change
        and posts at most 5 comments on GitHub. Each row below is one of those reviews. Open one to see what DiffMate
        said, why, and to tell us whether it helped.
      </p>
    </motion.section>
  );
}

function Runs() {
  const [runs, setRuns] = useState<Run[] | null>(null);
  const [cursor, setCursor] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load(after?: number) {
    api<{ items: Run[]; next_cursor: number | null }>(`/api/runs?limit=20${after ? `&cursor=${after}` : ""}`)
      .then((page) => {
        setRuns((prev) => [...(after ? (prev ?? []) : []), ...page.items]);
        setCursor(page.next_cursor);
      })
      .catch((e) => setError(e.message));
  }

  useEffect(load, []);

  if (error) return <p className="notice" role="alert">Could not load reviews: {error}</p>;
  if (!runs) return <p>Loading reviews…</p>;
  if (!runs.length)
    return (
      <>
        <Intro />
        <p className="notice">
          No reviews yet. Open or update a pull request in a repository where DiffMate is installed, and its review
          appears here within a minute or two.
        </p>
      </>
    );

  return (
    <>
      <Intro />
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Pull request</th>
              <th>Status</th>
              <th>Comments</th>
              <th>AI requests</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r, i) => (
              <motion.tr
                key={r.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: Math.min(i, 10) * 0.04, duration: 0.25 }}
              >
                <td>
                  <Link href={`/dashboard/runs/${r.id}`}>
                    {r.repo} #{r.pr}: {r.title}
                  </Link>
                </td>
                <td className={`status ${r.status}`}>{STATUS[r.status].label}</td>
                <td>{r.findings}</td>
                <td>{r.llm_requests}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
      {cursor && (
        <p>
          <button className="button quiet" onClick={() => load(cursor)}>
            Show older reviews
          </button>
        </p>
      )}
      <dl className="legend">
        {Object.values(STATUS).map((s) => (
          <div key={s.label}>
            <dt>{s.label}</dt>
            <dd>{s.help}</dd>
          </div>
        ))}
      </dl>
    </>
  );
}
