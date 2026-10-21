import { MotionConfig } from "motion/react";
import { Link, usePath } from "./lib/router";
import { Dashboard } from "./routes/Dashboard";
import { Landing } from "./routes/Landing";
import { RunDetail } from "./routes/RunDetail";

function Page({ path }: { path: string }) {
  if (path === "/") return <Landing />;
  if (path === "/dashboard") return <Dashboard />;
  const run = path.match(/^\/dashboard\/runs\/(\d+)$/);
  if (run) return <RunDetail id={Number(run[1])} />;
  return (
    <main className="wrap" style={{ padding: "4rem 1rem" }}>
      <h1 style={{ fontSize: "4rem" }}>Page not found</h1>
      <p>
        <Link href="/">Go to the home page</Link>
      </p>
    </main>
  );
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <Page path={usePath()} />
    </MotionConfig>
  );
}
