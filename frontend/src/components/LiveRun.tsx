import { useEffect, useState } from "react";
import { api } from "../lib/api";

// Plant a bug for real: opens a real pull request with this example's change in the public
// sandbox repo; DiffMate reviews it there, and this follows along. Hidden until the API
// says the sandbox is set up (docs/api.md, live demo).
type Opened = { pr: number; url: string };
type Review = { reviewed: boolean; url: string; comments: { line: number | null; body: string }[] };
type State =
  | { kind: "idle" }
  | { kind: "opening" }
  | { kind: "waiting"; opened: Opened; seconds: number }
  | { kind: "done"; opened: Opened; review: Review }
  | { kind: "error"; message: string };

const POLL_MS = 5000;
const GIVE_UP_S = 240;

// First line of DiffMate's comment, without its markdown bold markers.
const headline = (body: string) => body.split("\n")[0].replaceAll("**", "");

export function LiveRun({ example, label }: { example: string; label: string }) {
  const [enabled, setEnabled] = useState(false);
  const [state, setState] = useState<State>({ kind: "idle" });

  useEffect(() => {
    api<{ enabled: boolean }>("/api/demo")
      .then((r) => setEnabled(r.enabled))
      .catch(() => setEnabled(false));
  }, []);

  useEffect(() => setState({ kind: "idle" }), [example]);

  useEffect(() => {
    if (state.kind !== "waiting") return;
    const timer = setTimeout(async () => {
      try {
        const review = await api<Review>(`/api/demo/${state.opened.pr}`);
        if (review.reviewed) setState({ kind: "done", opened: state.opened, review });
        else if (state.seconds >= GIVE_UP_S) setState({ kind: "done", opened: state.opened, review });
        else setState({ ...state, seconds: state.seconds + POLL_MS / 1000 });
      } catch {
        setState({ ...state, seconds: state.seconds + POLL_MS / 1000 });
      }
    }, POLL_MS);
    return () => clearTimeout(timer);
  }, [state]);

  if (!enabled) return null;

  async function start() {
    setState({ kind: "opening" });
    try {
      const opened = await api<Opened>("/api/demo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ example }),
      });
      setState({ kind: "waiting", opened, seconds: 0 });
    } catch (e) {
      setState({ kind: "error", message: e instanceof Error ? e.message : "Something went wrong" });
    }
  }

  return (
    <div className="live-run" aria-live="polite">
      {(state.kind === "idle" || state.kind === "error") && (
        <button type="button" className="button" onClick={start}>
          Run "{label}" for real on GitHub
        </button>
      )}
      {state.kind === "idle" && (
        <p>Opens a real pull request with this change in a public sandbox repo. DiffMate reviews it live.</p>
      )}
      {state.kind === "error" && <p role="alert">{state.message}</p>}
      {state.kind === "opening" && <p>Opening a pull request…</p>}
      {state.kind === "waiting" && (
        <p>
          <a href={state.opened.url}>Pull request #{state.opened.pr}</a> is open. DiffMate is reviewing it now ({state.seconds}{" "}
          s).
        </p>
      )}
      {state.kind === "done" && (
        <p>
          {state.review.comments.length
            ? `DiffMate commented on line ${state.review.comments[0].line}: ${headline(state.review.comments[0].body)}. `
            : "No comment yet: it may be busy or out of free requests for today. "}
          <a href={state.opened.url}>See it on GitHub</a>
        </p>
      )}
    </div>
  );
}
