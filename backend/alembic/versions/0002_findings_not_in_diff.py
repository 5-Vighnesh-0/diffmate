"""Allow findings.status = 'dropped_not_in_diff' (approved 2026-10-07, Phase 2 gate).

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

OLD = "('posted', 'dropped_low_confidence', 'dropped_duplicate', 'dropped_over_cap')"
NEW = OLD[:-1] + ", 'dropped_not_in_diff')"


def upgrade() -> None:
    op.execute("alter table findings drop constraint findings_status_check")
    op.execute(f"alter table findings add constraint findings_status_check check (status in {NEW})")


def downgrade() -> None:
    op.execute("delete from findings where status = 'dropped_not_in_diff'")
    op.execute("alter table findings drop constraint findings_status_check")
    op.execute(f"alter table findings add constraint findings_status_check check (status in {OLD})")
