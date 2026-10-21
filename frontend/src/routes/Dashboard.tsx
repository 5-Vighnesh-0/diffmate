import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { Shell } from "../components/ui/Shell";
import { api, type Run } from "../lib/api";
import { Link } from "../lib/router";

// Plain-language status, written for people who have never used GitHub.
function statusSentence(r: Run) {
  switch (r.status) {
    case "queued":
      return "Waiting for its turn. Reviews run one at a time.";
    case "running":
      return "DiffMate is reading it right now.";
    case "failed":
      return "Something went wrong with this review. Open it to see why.";
    case "paused_daily_cap":
      // A paused review does not resume on its own: a new GitHub notice for the change resumes it (worker.py).
      return "Paused: DiffMate uses a free AI service with a daily limit, and today's limit was reached. It finishes the next time this change is updated after the limit resets.";
    case "done":
      return r.findings
        ? `DiffMate left ${r.findings} ${r.findings === 1 ? "note" : "notes"}.`
        : "DiffMate found nothing worth a note.";
  }
}

const HOW = [
  ["Someone proposes a change", "On GitHub, a change to a project's code is called a pull request."],
  ["GitHub tells DiffMate", "This happens automatically, within seconds, in projects where DiffMate is installed."],
  ["DiffMate reads the change", "Its AI looks for mistakes and security risks. This usually takes a minute or two."],
  ["It leaves notes", "Up to 5 short notes, each on the exact line it thinks is wrong. That set of notes is one review."],
];

const WORDS = [
  ["Pull request", "A proposed change to a project's code, waiting to be checked before it is accepted."],
  ["Review", "DiffMate's check of one pull request. Every new version of the change gets a new review."],
  ["Note", "A short comment DiffMate leaves on one line of code, explaining what looks wrong."],
];

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
        DiffMate checks proposed changes to your code and points out likely mistakes. Each card below is one of those
        checks. Open a card to read DiffMate's notes and tell us whether they helped.
      </p>
      <h2 className="mono steps-title">How a review happens</h2>
      <ol className="steps">
        {HOW.map(([title, body]) => (
          <li key={title}>
            <strong>{title}.</strong> {body}
          </li>
        ))}
      </ol>
    </motion.section>
  );
}

function Summary({ runs, more }: { runs: Run[]; more: boolean }) {
  const notes = runs.reduce((n, r) => n + r.findings, 0);
  const waiting = runs.filter((r) => r.status === "queued" || r.status === "running").length;
  const plus = more ? "+" : "";
  return (
    <dl className="summary">
      <div>
        <dd>
          {runs.length}
          {plus}
        </dd>
        <dt>{runs.length === 1 ? "review" : "reviews"} so far</dt>
      </div>
      <div>
        <dd>
          {notes}
          {plus}
        </dd>
        <dt>notes left on code</dt>
      </div>
      <div>
        <dd>{waiting}</dd>
        <dt>waiting or in progress</dt>
      </div>
    </dl>
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

  return (
    <>
      <Intro />
      {runs.length === 0 ? (
        <p className="notice">
          No reviews yet. When someone proposes a change in a project where DiffMate is installed, its review appears
          here within a minute or two.
        </p>
      ) : (
        <>
          <Summary runs={runs} more={cursor !== null} />
          <ul className="review-cards">
            {runs.map((r, i) => (
              <motion.li
                key={r.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i, 10) * 0.05, duration: 0.25 }}
              >
                <Link href={`/dashboard/runs/${r.id}`} className={`review-card ${r.status}`}>
                  <span className="card-title">"{r.title}"</span>
                  <span>
                    Change #{r.pr} in {r.repo}. Reviewed {new Date(r.created_at).toLocaleDateString()}.
                  </span>
                  <span className="card-status">{statusSentence(r)}</span>
                </Link>
              </motion.li>
            ))}
          </ul>
          {cursor && (
            <p>
              <button className="button quiet" onClick={() => load(cursor)}>
                Show older reviews
              </button>
            </p>
          )}
        </>
      )}
      <section className="intro">
        <h2 className="mono steps-title">Words you will see</h2>
        <dl className="words">
          {WORDS.map(([word, meaning]) => (
            <div key={word}>
              <dt>{word}</dt>
              <dd>{meaning}</dd>
            </div>
          ))}
        </dl>
      </section>
    </>
  );
}
