"""ORM mapping of the approved schema. The tables and constraints themselves come from the
Alembic migration (docs/architecture.md -> Data model); these classes only mirror them."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    type_annotation_map = {int: BigInteger, dict[str, Any]: JSONB}


class Installation(Base):
    __tablename__ = "installations"
    id: Mapped[int] = mapped_column(primary_key=True)
    github_installation_id: Mapped[int]
    account_login: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default="now()")


class Repo(Base):
    __tablename__ = "repos"
    id: Mapped[int] = mapped_column(primary_key=True)
    installation_id: Mapped[int] = mapped_column(ForeignKey("installations.id"))
    github_repo_id: Mapped[int]
    full_name: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default="now()")
    installation: Mapped[Installation] = relationship()


class PullRequest(Base):
    __tablename__ = "pull_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    repo_id: Mapped[int] = mapped_column(ForeignKey("repos.id"))
    number: Mapped[int]
    title: Mapped[str]
    repo: Mapped[Repo] = relationship()


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    pull_request_id: Mapped[int] = mapped_column(ForeignKey("pull_requests.id"))
    commit_sha: Mapped[str]
    status: Mapped[str] = mapped_column(server_default="queued")
    llm_requests: Mapped[int] = mapped_column(server_default="0")
    tokens_in: Mapped[int] = mapped_column(server_default="0")
    tokens_out: Mapped[int] = mapped_column(server_default="0")
    est_cost_usd: Mapped[Decimal] = mapped_column(server_default="0")
    error: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default="now()")
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    source: Mapped[str]
    file: Mapped[str]
    line: Mapped[int]
    category: Mapped[str]
    severity: Mapped[str]
    confidence: Mapped[Decimal]
    explanation: Mapped[str]
    status: Mapped[str]
    github_comment_id: Mapped[int | None]


class TraceStep(Base):
    __tablename__ = "trace_steps"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    step_no: Mapped[int]
    tool: Mapped[str]
    summary: Mapped[str]
    tokens_in: Mapped[int] = mapped_column(server_default="0")
    tokens_out: Mapped[int] = mapped_column(server_default="0")
    duration_ms: Mapped[int] = mapped_column(server_default="0")


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"))
    github_user_id: Mapped[int]
    verdict: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default="now()")


class BenchmarkCase(Base):
    __tablename__ = "benchmark_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    kind: Mapped[str]
    split: Mapped[str]
    source_repo: Mapped[str]
    source_url: Mapped[str | None]
    license: Mapped[str]
    labels: Mapped[dict[str, Any]]
    frozen_at: Mapped[datetime | None]


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch: Mapped[str]
    case_id: Mapped[int] = mapped_column(ForeignKey("benchmark_cases.id"))
    setup: Mapped[str]
    model: Mapped[str | None]
    metrics: Mapped[dict[str, Any]]
    created_at: Mapped[datetime] = mapped_column(server_default="now()")
