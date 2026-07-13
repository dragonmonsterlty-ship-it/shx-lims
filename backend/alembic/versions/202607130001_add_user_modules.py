"""add user modules

Revision ID: 202607130001
Revises: 202606290001
Create Date: 2026-07-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202607130001"
down_revision: str | None = "202606290001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("modules", sa.String(length=100), server_default="lims", nullable=False),
    )
    op.execute(sa.text('UPDATE "user" SET modules = \'lims\' WHERE modules IS NULL OR modules = \'\''))


def downgrade() -> None:
    op.drop_column("user", "modules")
