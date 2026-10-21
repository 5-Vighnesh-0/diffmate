import { useEffect, useState } from "react";
import { Shell } from "../components/ui/Shell";
import { api, type Run } from "../lib/api";
import { Link } from "../lib/router";

const STATUS: Record<Run["status"], string> = {
  queued: "Waiting",
  running: "Reviewing",
  done: "Done",
  failed: "Failed",
  paused_daily_cap: "Paused: free daily limit reached",
};

export function Dashboard() {
  return <Shell>{() => <Runs />}</Shell>;
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
      <p className="notice">
        No reviews yet. Open or update a pull request in a repository where DiffMate is installed, and its review
        appears here.
      </p>
    );

  return (
    <>
      <h1 style={{ fontSize: "3rem", marginBottom: "1rem" }}>Reviews</h1>
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
            {runs.map((r) => (
              <tr key={r.id}>
                <td>
                  <Link href={`/dashboard/runs/${r.id}`}>
                    {r.repo} #{r.pr}: {r.title}
                  </Link>
                </td>
                <td className={`status ${r.status}`}>{STATUS[r.status]}</td>
                <td>{r.findings}</td>
                <td>{r.llm_requests}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
              </tr>
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
    </>
  );
}
