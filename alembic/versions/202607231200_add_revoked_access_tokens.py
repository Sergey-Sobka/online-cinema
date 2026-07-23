"""add revoked access tokens

Revision ID: 202607231200
Revises: 664b1af948f1
Create Date: 2026-07-23 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "202607231200"
down_revision: str | None = "664b1af948f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "revoked_access_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("jti", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
    )
    op.create_index(
        op.f("ix_revoked_access_tokens_expires_at"),
        "revoked_access_tokens",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_revoked_access_tokens_expires_at"),
        table_name="revoked_access_tokens",
    )
    op.drop_table("revoked_access_tokens")
