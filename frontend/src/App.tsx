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

// Page changes: a CSS fade-in keyed by path (DESIGN.md T12). No exit animation, so a new
// page never waits on the old one.
function Routes({ path }: { path: string }) {
  return (
    <div key={path} className="page-in">
      <Page path={path} />
    </div>
  );
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <Routes path={usePath()} />
    </MotionConfig>
  );
}
