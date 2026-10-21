import { motion } from "motion/react";
import { LOGIN_URL } from "../../lib/api";
import demo from "../../lib/demo.json";

// A real recorded review (benchmark/demo.py), shown so visitors see what they are signing in for.
const example = demo.breaks.shell;
const exampleComment = example.comments[0];
const exampleLine = example.after.split("\n")[exampleComment.line - 1];

const STEPS = [
  ["Sign in with GitHub", "GitHub may ask you to approve DiffMate the first time. Then you come straight back here."],
  ["See your reviews", "One row for every pull request DiffMate reviewed in your repositories, newest first."],
  ["Rate the comments", "Mark each comment Useful or Not useful. That is how DiffMate measures how often it is right."],
];

export function SignIn() {
  return (
    <section className="signin">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      >
        <h1>See what DiffMate found in your pull requests</h1>
        <p className="lead">
          Your dashboard shows every review DiffMate has done on your repositories: what it said, where, and the steps it
          took to decide.
        </p>
        <a className="button big" href={LOGIN_URL}>
          Sign in with GitHub
        </a>
        <h2 className="mono steps-title">What happens next</h2>
        <ol className="steps">
          {STEPS.map(([title, body], i) => (
            <motion.li
              key={title}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 + i * 0.08, duration: 0.3 }}
            >
              <strong>{title}.</strong> {body}
            </motion.li>
          ))}
        </ol>
        <p className="fine">
          DiffMate uses your GitHub sign-in only to see which repositories you can access. It never stores your GitHub
          token, never posts as you, and never changes your code. You stay signed in for 8 hours. Only repositories
          where the DiffMate GitHub App is installed have reviews.
        </p>
      </motion.div>

      <motion.figure
        className="example"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      >
        <figcaption className="mono">What a review looks like</figcaption>
        <ol className="code small" aria-label={`${demo.path}, line ${exampleComment.line}`}>
          <li className="changed">
            <span className="n">{exampleComment.line}</span>
            <span className="t">{exampleLine.trim()}</span>
          </li>
        </ol>
        <aside className="review-comment">
          <p className="mono">
            diffmate[bot] on line {exampleComment.line}: {exampleComment.category}, {exampleComment.severity}
          </p>
          <p>{exampleComment.explanation}</p>
        </aside>
        <p className="fine mono">Real output, recorded {demo.recorded}.</p>
      </motion.figure>
    </section>
  );
}
