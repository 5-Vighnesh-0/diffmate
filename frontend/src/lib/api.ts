// Dashboard API client (docs/api.md). The session lives in an HttpOnly cookie the API sets.
export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const LOGIN_URL = `${API_URL}/auth/login`;
// The public GitHub App (made public 2026-10-21). GitHub asks the visitor to sign in first.
export const INSTALL_URL = "https://github.com/apps/diffmate-vighnesh/installations/new";

export type Me = {
  user: { id: number; login: string };
  installations: number[];
  csrf_token: string;
  llm: { requests_today: number; daily_cap: number };
};

export type Run = {
  id: number;
  repo: string;
  pr: number;
  title: string;
  commit_sha: string;
  status: "queued" | "running" | "done" | "failed" | "paused_daily_cap";
  error: string | null;
  llm_requests: number;
  est_cost_usd: number;
  findings: number;
  created_at: string;
  finished_at: string | null;
};

export type Verdict = "accept" | "reject";

export type Finding = {
  id: number;
  file: string;
  line: number;
  category: string;
  severity: string;
  confidence: number;
  explanation: string; // LLM text: render as plain text only
  status: string;
  my_verdict: Verdict | null;
};

export type TraceStep = {
  step_no: number;
  tool: string;
  summary: string;
  tokens_in: number;
  tokens_out: number;
  duration_ms: number;
};

export type FeedbackSummary = { useful: number; not_useful: number };

// "4 of 5 notes useful (80%)", or null before any vote.
export function usefulLine(s: FeedbackSummary): string | null {
  const total = s.useful + s.not_useful;
  if (!total) return null;
  return `${s.useful} of your ${total} rated ${total === 1 ? "note" : "notes"} useful (${Math.round((s.useful / total) * 100)}%)`;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(API_URL + path, { credentials: "include", ...init });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, body?.error?.message ?? `Request failed (${res.status})`);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export function post(path: string, csrf: string, body?: unknown) {
  return api<void>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
