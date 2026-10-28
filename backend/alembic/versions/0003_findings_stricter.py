"""Allow findings.status = 'dropped_stricter' (learn from votes; approved 2026-10-27).

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

OLD = "('posted', 'dropped_low_confidence', 'dropped_duplicate', 'dropped_over_cap', 'dropped_not_in_diff')"
NEW = OLD[:-1] + ", 'dropped_stricter')"


def upgrade() -> None:
    op.execute("alter table findings drop constraint findings_status_check")
    op.execute(f"alter table findings add constraint findings_status_check check (status in {NEW})")


def downgrade() -> None:
    op.execute(
        "update findings set status = 'dropped_low_confidence' where status = 'dropped_stricter'"
    )
    op.execute("alter table findings drop constraint findings_status_check")
    op.execute(f"alter table findings add constraint findings_status_check check (status in {OLD})")
