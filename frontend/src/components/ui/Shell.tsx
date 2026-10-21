import { type ReactNode, useEffect, useState } from "react";
import { api, ApiError, type Me, post } from "../../lib/api";
import { Link, navigate } from "../../lib/router";
import { SignIn } from "./SignIn";

type State = { kind: "loading" } | { kind: "signed-out" } | { kind: "error"; message: string } | { kind: "ok"; me: Me };

// Dashboard frame: who is signed in, today's free AI quota, sign out.
export function Shell({ children }: { children: (me: Me) => ReactNode }) {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    api<Me>("/api/me")
      .then((me) => setState({ kind: "ok", me }))
      .catch((e) =>
        setState(e instanceof ApiError && e.status === 401 ? { kind: "signed-out" } : { kind: "error", message: e.message }),
      );
  }, []);

  async function signOut(me: Me) {
    await post("/auth/logout", me.csrf_token).catch(() => undefined);
    navigate("/");
  }

  return (
    <div className="wrap">
      <header className="app-bar">
        <Link href="/" className="brand">
          DiffMate
        </Link>
        {state.kind === "ok" && (
          <div style={{ display: "flex", gap: "1rem", alignItems: "center", flexWrap: "wrap" }}>
            <span>{state.me.user.login}</span>
            <span className="mono">
              Free AI requests today: {state.me.llm.requests_today} of {state.me.llm.daily_cap}
            </span>
            <button className="button quiet" onClick={() => signOut(state.me)}>
              Sign out
            </button>
          </div>
        )}
      </header>
      <main style={{ padding: "1.5rem 0 4rem" }}>
        {state.kind === "loading" && <p>Loading…</p>}
        {state.kind === "signed-out" && <SignIn />}
        {state.kind === "error" && (
          <p className="notice" role="alert">
            Could not reach the DiffMate API: {state.message}. Check that the backend is running, then reload.
          </p>
        )}
        {state.kind === "ok" && children(state.me)}
      </main>
    </div>
  );
}
