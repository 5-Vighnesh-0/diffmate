"""Initial schema, approved 2026-10-07 (docs/architecture.md -> Data model).

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = """
create table installations (
  id bigint generated always as identity primary key,
  github_installation_id bigint not null unique,
  account_login text not null,
  created_at timestamptz not null default now()
);

create table repos (
  id bigint generated always as identity primary key,
  installation_id bigint not null references installations(id) on delete cascade,
  github_repo_id bigint not null unique,
  full_name text not null,
  created_at timestamptz not null default now()
);
create index repos_installation_id_idx on repos (installation_id);

create table pull_requests (
  id bigint generated always as identity primary key,
  repo_id bigint not null references repos(id) on delete cascade,
  number integer not null check (number > 0),
  title text not null check (length(title) <= 300),  -- untrusted; shown as plain text only
  unique (repo_id, number)
);

create table runs (
  id bigint generated always as identity primary key,
  pull_request_id bigint not null references pull_requests(id) on delete cascade,
  commit_sha text not null check (commit_sha ~ '^[0-9a-f]{40}$'),
  status text not null default 'queued'
    check (status in ('queued', 'running', 'done', 'failed', 'paused_daily_cap')),
  llm_requests integer not null default 0,
  tokens_in integer not null default 0,
  tokens_out integer not null default 0,
  est_cost_usd numeric(10, 6) not null default 0,  -- estimate at list price; actual spend is $0
  error text check (length(error) <= 500),         -- short reason, never secrets or diffs
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz,
  unique (pull_request_id, commit_sha)
);

create table findings (
  id bigint generated always as identity primary key,
  run_id bigint not null references runs(id) on delete cascade,
  source text not null check (source in ('linter', 'agent')),
  file text not null check (length(file) <= 500),
  line integer not null check (line > 0),
  category text not null check (category in ('bug', 'security', 'missing_test')),
  severity text not null check (severity in ('low', 'medium', 'high')),
  confidence numeric(3, 2) not null check (confidence between 0 and 1),
  explanation text not null check (length(explanation) <= 2000),
  status text not null
    check (status in ('posted', 'dropped_low_confidence', 'dropped_duplicate', 'dropped_over_cap')),
  github_comment_id bigint
);
create index findings_run_id_idx on findings (run_id);

create table trace_steps (
  id bigint generated always as identity primary key,
  run_id bigint not null references runs(id) on delete cascade,
  step_no integer not null check (step_no > 0),
  tool text not null,
  summary text not null check (length(summary) <= 500),  -- e.g. "read_file app/x.py lines 10-40"; no contents
  tokens_in integer not null default 0,
  tokens_out integer not null default 0,
  duration_ms integer not null default 0,
  unique (run_id, step_no)
);

create table feedback (
  id bigint generated always as identity primary key,
  finding_id bigint not null references findings(id) on delete cascade,
  github_user_id bigint not null,
  verdict text not null check (verdict in ('accept', 'reject')),
  created_at timestamptz not null default now(),
  unique (finding_id, github_user_id)
);

create table benchmark_cases (
  id bigint generated always as identity primary key,
  name text not null unique,
  kind text not null check (kind in ('real', 'seeded')),
  split text not null check (split in ('dev', 'holdout')),
  source_repo text not null,
  source_url text,
  license text not null,
  labels jsonb not null,           -- expected findings: file, line, category
  frozen_at timestamptz
);

create table benchmark_runs (
  id bigint generated always as identity primary key,
  batch text not null,             -- e.g. "2026-10-30-ab12cd3" (date + git sha)
  case_id bigint not null references benchmark_cases(id) on delete cascade,
  setup text not null check (setup in ('linter_only', 'agent_only', 'agent_filtered')),
  model text,
  metrics jsonb not null,          -- tp, fp, fn, latency_ms, tokens_in, tokens_out, est_cost_usd
  created_at timestamptz not null default now(),
  unique (batch, case_id, setup)
);
create index benchmark_runs_case_id_idx on benchmark_runs (case_id);
"""

TABLES = [
    "benchmark_runs",
    "benchmark_cases",
    "feedback",
    "trace_steps",
    "findings",
    "runs",
    "pull_requests",
    "repos",
    "installations",
]


def statements(sql: str) -> list[str]:
    # asyncpg runs one command per call; drop "--" comments (none inside strings), split on ";".
    code = "\n".join(line.split("--", 1)[0] for line in sql.splitlines())
    return [s.strip() for s in code.split(";") if s.strip()]


def upgrade() -> None:
    for statement in statements(SCHEMA):
        op.execute(statement)


def downgrade() -> None:
    for table in TABLES:
        op.drop_table(table)
