// Timeline of one recorded review for the landing page's scroll flow. Times are seconds;
// "real" time starts at 0 when the visitor's change begins and INTRO is "Create pull request".
// Recorded: the change, the comment, the order of the AI's requests and the total seconds.
// Estimated: when each AI request happened inside that total (the recording kept only the total).
import type demo from "./demo.json";

export type Run = (typeof demo.breaks)["loop"];
export type Step = "verify" | "diff" | "ai" | "filter" | "post";
export type FlowEvent = {
  at: number;
  who: "you" | "github" | "diffmate" | "AI";
  side: "github" | "diffmate";
  text: string;
  step?: Step;
  key?: boolean;
};
type Segment = { v0: number; v1: number; r0: number; rate: number };

export const INTRO = 6; // the visitor's own change, before the clock starts
export const OUTRO = 4;
export const HOLD = 2.2; // the scroll holds still at the catch
const AI_SHOWN = 10; // the AI's waiting is squeezed into about this much flow time

export function timeline(run: Run, clean: string) {
  const seconds = run.seconds;
  const aiFrom = INTRO + 1.6;
  const aiTo = INTRO + seconds - 1.1;
  const hit = INTRO + seconds;
  const end = hit + OUTRO;
  const rate = Math.max(1, (aiTo - aiFrom) / AI_SHOWN);

  const segments: Segment[] = [];
  let v = 0;
  let r = 0;
  for (const [until, k] of [[aiFrom, 1], [aiTo, rate], [hit, 1], [hit, 0], [end, 1]]) {
    const dur = k === 0 ? HOLD : (until - r) / k;
    segments.push({ v0: v, v1: v + dur, r0: r, rate: k });
    v += dur;
    if (k !== 0) r = until;
  }

  const c = run.comments[0];
  const changed = changeOf(clean, run.after).added.length;
  const per = (aiTo - aiFrom) / run.trace.length;
  const lines = (n: number) => `${n} changed line${n === 1 ? "" : "s"}`;
  const events: FlowEvent[] = [
    { at: INTRO - 0.6, who: "you", side: "github", text: 'You click "Create pull request"', key: true },
    { at: INTRO, who: "github", side: "diffmate", text: "GitHub sends DiffMate the webhook", key: true },
    { at: INTRO + 0.15, who: "diffmate", side: "diffmate", text: "Signature checked: genuine", step: "verify" },
    { at: INTRO + 0.25, who: "diffmate", side: "diffmate", text: "Public repo, not a repeat; job queued" },
    { at: INTRO + 0.55, who: "diffmate", side: "diffmate", text: "Worker gets a token for this repo only" },
    { at: INTRO + 0.9, who: "github", side: "diffmate", text: `Diff received: ${lines(changed)}`, step: "diff" },
    { at: INTRO + 1.25, who: "diffmate", side: "diffmate", text: "Linters run on the changed file" },
    ...run.trace.map(
      (call, j): FlowEvent => ({
        at: aiFrom + j * per,
        who: "AI",
        side: "diffmate",
        text: `Request ${j + 1}: ${call.split("(")[0]}`,
        step: j === 0 ? "ai" : undefined,
      }),
    ),
    {
      at: hit - 0.95,
      who: "diffmate",
      side: "diffmate",
      text: `Filter passes the note (${Math.round(c.confidence * 100)}% sure)`,
      step: "filter",
    },
    { at: hit - 0.45, who: "diffmate", side: "diffmate", text: "Posting the comment to GitHub" },
    { at: hit, who: "github", side: "github", text: `Comment appears on line ${c.line}`, step: "post", key: true },
  ];

  const chapters: [number, string][] = [
    [0, "You make a change"],
    [INTRO - 0.6, "You open the PR"],
    [INTRO, "GitHub calls DiffMate"],
    [INTRO + 0.9, "It reads the diff"],
    [aiFrom, "The AI investigates"],
    [hit - 0.95, "The filter"],
    [hit, "The catch"],
    [hit + 0.6, "Your turn"],
  ];

  return { run, seconds, aiFrom, aiTo, hit, end, per, segments, duration: v, events, chapters };
}

export type Timeline = ReturnType<typeof timeline>;

/** Real time at flow time v (flow time is what the scroll drives). */
export function realAt(tl: Timeline, v: number): number {
  for (const s of tl.segments) if (v <= s.v1) return s.rate === 0 ? s.r0 : s.r0 + (v - s.v0) * s.rate;
  return tl.end;
}

/** Flow time at which real time r is reached (the start of a hold, if r is the catch). */
export function playAt(tl: Timeline, r: number): number {
  for (const s of tl.segments) {
    if (s.rate !== 0 && r <= s.r0 + (s.v1 - s.v0) * s.rate) return s.v0 + (r - s.r0) / s.rate;
  }
  return tl.duration;
}

export type Line = { n: number | null; kind: "same" | "del" | "add"; text: string };

/** Lines of the pull request's file with the change shown as removed then added lines. The
 * change is what lies between the lines both versions share at the start and at the end, so
 * changes that add or remove lines work too. */
export function changeOf(clean: string, after: string) {
  const before = clean.replace(/\n$/, "").split("\n");
  const now = after.replace(/\n$/, "").split("\n");
  let head = 0;
  while (head < before.length && head < now.length && before[head] === now[head]) head++;
  let tail = 0;
  while (
    tail < before.length - head &&
    tail < now.length - head &&
    before[before.length - 1 - tail] === now[now.length - 1 - tail]
  )
    tail++;
  const removed = before.slice(head, before.length - tail);
  const added = now.slice(head, now.length - tail);
  const lines: Line[] = [
    ...now.slice(0, head).map((text, i): Line => ({ n: i + 1, kind: "same", text })),
    ...removed.map((text): Line => ({ n: null, kind: "del", text })),
    ...added.map((text, i): Line => ({ n: head + i + 1, kind: "add", text })),
    ...now.slice(now.length - tail).map((text, i): Line => ({ n: now.length - tail + i + 1, kind: "same", text })),
  ];
  return { lines, first: head + 1, removed, added };
}
