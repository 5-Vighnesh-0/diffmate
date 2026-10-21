import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LOGIN_URL } from "../../src/lib/api";
import demo from "../../src/lib/demo.json";
import { Dashboard } from "../../src/routes/Dashboard";
import { Landing } from "../../src/routes/Landing";
import { RunDetail } from "../../src/routes/RunDetail";
import { stubBrowser } from "./setup";

const ME = { user: { id: 1, login: "octo" }, installations: [9], csrf_token: "tok", llm: { requests_today: 3, daily_cap: 400 } };

function json(body: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(body), { status });
}

// Fake API: route -> response. Records every request.
function fakeApi(routes: Record<string, () => Response>) {
  const fetch = vi.fn(async (url: string, init?: RequestInit) => {
    const path = new URL(url).pathname;
    const key = `${init?.method ?? "GET"} ${path}`;
    if (!routes[key]) throw new Error(`unexpected ${key}`);
    return routes[key]();
  });
  vi.stubGlobal("fetch", fetch);
  return fetch;
}

describe("dashboard", () => {
  it("asks a signed-out visitor to sign in with GitHub", async () => {
    fakeApi({ "GET /api/me": () => json({ error: { code: "unauthorized", message: "Not signed in" } }, 401) });

    render(<Dashboard />);

    const link = await screen.findByRole("link", { name: "Sign in with GitHub" });
    expect(link.getAttribute("href")).toBe(LOGIN_URL);
    expect(screen.getByRole("heading", { name: "What happens next" })).toBeTruthy();
    expect(screen.getByText(/never stores your GitHub token/)).toBeTruthy();
    expect(screen.getByText(demo.breaks.shell.comments[0].explanation)).toBeTruthy(); // the real example
  });

  it("explains each review in plain words and how reviews happen", async () => {
    fakeApi({
      "GET /api/me": () => json(ME),
      "GET /api/runs": () =>
        json({
          items: [
            { id: 1, repo: "o/r", pr: 4, title: "Add calc", commit_sha: "abc1234", status: "done", error: null,
              llm_requests: 5, est_cost_usd: 0.004, findings: 3, created_at: "2026-10-21T00:00:00Z", finished_at: null },
            { id: 2, repo: "o/r", pr: 5, title: "Fix login", commit_sha: "def5678", status: "paused_daily_cap",
              error: null, llm_requests: 0, est_cost_usd: 0, findings: 0, created_at: "2026-10-21T00:00:00Z",
              finished_at: null },
          ],
          next_cursor: null,
        }),
      "GET /api/feedback/summary": () => json({ useful: 3, not_useful: 1 }),
    });

    render(<Dashboard />);

    expect(await screen.findByText("DiffMate left 3 notes.")).toBeTruthy();
    expect(screen.getByText(/finishes the next time this change is updated/)).toBeTruthy();
    expect(screen.getByRole("heading", { name: "How a review happens" })).toBeTruthy();
    expect(screen.getByText("reviews so far")).toBeTruthy();
    expect(screen.getByText("Pull request")).toBeTruthy();
    expect(await screen.findByText("75%")).toBeTruthy();
    expect(screen.getByText("of your 4 rated notes were useful")).toBeTruthy();
  });

  it("shows AI text as plain text and sends votes with the CSRF token", async () => {
    const evil = '<img src=x onerror="alert(1)"> see https://evil.example';
    const fetch = fakeApi({
      "GET /api/me": () => json(ME),
      "GET /api/runs/7": () =>
        json({
          id: 7, repo: "o/r", pr: 2, title: "Add calc", commit_sha: "abcdef1234", status: "done", error: null,
          llm_requests: 4, est_cost_usd: 0.004, created_at: "2026-10-21T00:00:00Z", finished_at: null,
          findings: [{ id: 5, file: "calc.py", line: 3, category: "bug", severity: "high", confidence: 0.9,
            explanation: evil, status: "posted", my_verdict: null }],
        }),
      "GET /api/runs/7/trace": () => json([]),
      "POST /api/findings/5/feedback": () => json(null, 204),
      "GET /api/feedback/summary": () => json({ useful: 4, not_useful: 1 }),
    });

    const { container } = render(<RunDetail id={7} />);

    expect(await screen.findByText(evil)).toBeTruthy();
    expect(container.querySelector("img")).toBeNull();

    expect(screen.getByText(/saved only in DiffMate, never on GitHub/)).toBeTruthy();
    expect(screen.getByText("You have rated 0 of 1.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "See the change on GitHub" }).getAttribute("href")).toBe(
      "https://github.com/o/r/pull/2",
    );

    fireEvent.click(screen.getByRole("button", { name: "Useful" }));

    expect(await screen.findByText(/So far you've found 4 of your 5 rated notes useful \(80%\)\./)).toBeTruthy();
    expect(screen.getByText(/Saved: useful\./)).toBeTruthy();
    expect(screen.getByText("You have rated 1 of 1.")).toBeTruthy();

    await waitFor(() => expect(screen.getByRole("button", { name: "Useful" }).getAttribute("aria-pressed")).toBe("true"));
    const [, init] = fetch.mock.calls.find(([url]) => String(url).endsWith("/feedback"))!;
    expect(init?.method).toBe("POST");
    expect((init?.headers as Record<string, string>)["X-CSRF-Token"]).toBe("tok");
    expect(init?.credentials).toBe("include");
    expect(JSON.parse(String(init?.body))).toEqual({ verdict: "accept" });
  });
});

describe("landing", () => {
  it("shows the whole recorded review, still, when the visitor prefers reduced motion", () => {
    stubBrowser({ reduceMotion: true });

    render(<Landing />);

    expect(screen.getByTestId("review-still")).toBeTruthy();
    expect(screen.queryByTestId("review-pinned")).toBeNull();
    expect(screen.getByText(demo.peak.comments[0].explanation)).toBeTruthy();
    const bug = document.querySelector(".bug-line");
    expect(bug?.classList.contains("hit")).toBe(true);
  });

  it("pins the review so scroll can write it when motion is allowed", () => {
    render(<Landing />);

    expect(screen.getByTestId("review-pinned")).toBeTruthy();
  });

  it("shows what DiffMate actually said about the bug the visitor plants", () => {
    render(<Landing />);

    fireEvent.click(screen.getByRole("radio", { name: "Run tar through the shell" }));

    expect(screen.getByText(demo.breaks.shell.comments[0].explanation)).toBeTruthy();
    expect(screen.getByText(/Not live\./)).toBeTruthy();
  });
});
