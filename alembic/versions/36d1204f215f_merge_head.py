"""merge head

Revision ID: 36d1204f215f
Revises: 202607061000, b8c9e20fef27
Create Date: 2026-07-07 13:16:28.847273

"""

from collections.abc import Sequence

revision: str = "36d1204f215f"
down_revision: str | None = ("202607061000", "b8c9e20fef27")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
