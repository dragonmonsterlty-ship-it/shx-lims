"""enhance project summary fields

Revision ID: 202606230002
Revises: 202606220002
Create Date: 2026-06-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202606230002"
down_revision: str | None = "202606220002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("project", sa.Column("priority", sa.String(length=10), server_default="normal", nullable=False))
    op.add_column("project", sa.Column("current_stage", sa.String(length=100), nullable=True))
    op.add_column("project", sa.Column("progress", sa.Integer(), server_default="0", nullable=False))
    op.add_column("project", sa.Column("recent_update", sa.Text(), nullable=True))
    op.add_column("project", sa.Column("risk_summary", sa.Text(), nullable=True))
    op.add_column("project", sa.Column("next_plan", sa.Text(), nullable=True))
    op.add_column("project", sa.Column("remark", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("project", "remark")
    op.drop_column("project", "next_plan")
    op.drop_column("project", "risk_summary")
    op.drop_column("project", "recent_update")
    op.drop_column("project", "progress")
    op.drop_column("project", "current_stage")
    op.drop_column("project", "priority")
