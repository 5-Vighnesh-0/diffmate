import { describe, expect, it } from "vitest";
import demo from "../../src/lib/demo.json";
import { changeOf, HOLD, INTRO, playAt, realAt, timeline } from "../../src/lib/flow";

const run = demo.breaks.loop;

describe("review flow timeline", () => {
  const tl = timeline(run, demo.clean);

  it("starts the clock when the pull request opens and ends with the recorded comment time", () => {
    const opened = tl.events.find((e) => e.who === "github")!;
    const posted = tl.events[tl.events.length - 1];
    expect(opened.at).toBe(INTRO);
    expect(posted.at - INTRO).toBeCloseTo(run.seconds);
    expect(posted.step).toBe("post");
  });

  it("keeps events in time order with one AI event per recorded request", () => {
    const ats = tl.events.map((e) => e.at);
    expect(ats).toEqual([...ats].sort((a, b) => a - b));
    expect(tl.events.filter((e) => e.who === "AI")).toHaveLength(run.trace.length);
  });

  it("squeezes the AI's waiting and holds still at the catch", () => {
    expect(tl.duration).toBeLessThan(tl.end); // shorter than real time
    const atCatch = playAt(tl, tl.hit);
    expect(realAt(tl, atCatch)).toBeCloseTo(tl.hit);
    expect(realAt(tl, atCatch + HOLD / 2)).toBeCloseTo(tl.hit); // the hold
    expect(realAt(tl, tl.duration)).toBeCloseTo(tl.end);
  });

  it("maps flow time to real time and back", () => {
    for (const r of [0, 3, INTRO, tl.aiFrom + 2, tl.aiTo - 1, tl.hit + 1]) {
      expect(realAt(tl, playAt(tl, r))).toBeCloseTo(r);
    }
    let prev = -1;
    for (let v = 0; v <= tl.duration; v += 0.25) {
      const r = realAt(tl, v);
      expect(r).toBeGreaterThanOrEqual(prev);
      prev = r;
    }
  });
});

describe("changeOf", () => {
  it("finds the changed lines between the clean file and the pull request", () => {
    const c = changeOf(demo.clean, run.after);
    expect(c.first).toBe(8);
    expect(c.removed).toEqual(["    for v in values:", "        total += v"]);
    expect(c.added).toEqual(["    for i in range(1, len(values)):", "        total += values[i]"]);
    expect(c.lines.filter((l) => l.kind === "add").map((l) => l.n)).toEqual([8, 9]);
  });
});
