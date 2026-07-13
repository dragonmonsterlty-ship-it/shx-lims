"""expand user role length

Revision ID: 202606290001
Revises: 202606260001
Create Date: 2026-06-29
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202606290001"
down_revision: str | None = "202606260001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.String(length=20),
            type_=sa.String(length=64),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("user") as batch_op:
        batch_op.alter_column(
            "role",
            existing_type=sa.String(length=64),
            type_=sa.String(length=20),
            existing_nullable=False,
        )
