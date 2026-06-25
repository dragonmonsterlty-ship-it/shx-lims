"""complete T1.4 business flows

Revision ID: 202606250001
Revises: 202606230004
Create Date: 2026-06-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202606250001"
down_revision: str | None = "202606230004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiment_record_participant",
        sa.Column("experiment_record_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_record_id"], ["experiment_record.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("experiment_record_id", "user_id"),
    )
    op.add_column(
        "experiment_reagent_usage",
        sa.Column("outbound_status", sa.String(length=20), server_default="pending", nullable=False),
    )
    op.add_column("experiment_reagent_usage", sa.Column("shortage_qty", sa.Numeric(18, 4), nullable=True))
    op.add_column("experiment_reagent_usage", sa.Column("dispensed_by", sa.BigInteger(), nullable=True))
    op.add_column("experiment_reagent_usage", sa.Column("dispensed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "inventory_txn",
        sa.Column("source_type", sa.String(length=20), server_default="manual", nullable=False),
    )
    op.add_column("inventory_txn", sa.Column("source_id", sa.BigInteger(), nullable=True))
    op.add_column("inventory_txn", sa.Column("shortage_qty", sa.Numeric(18, 4), nullable=True))

    op.execute("UPDATE \"user\" SET role = 'project_manager' WHERE role = 'pm'")
    op.execute("UPDATE \"user\" SET role = 'operator' WHERE role IN ('researcher', 'analyst', 'qa')")
    op.execute("UPDATE daily_report SET status = 'confirmed' WHERE status = 'reviewed'")


def downgrade() -> None:
    op.execute("UPDATE daily_report SET status = 'reviewed' WHERE status = 'confirmed'")
    op.drop_column("inventory_txn", "shortage_qty")
    op.drop_column("inventory_txn", "source_id")
    op.drop_column("inventory_txn", "source_type")
    op.drop_column("experiment_reagent_usage", "dispensed_at")
    op.drop_column("experiment_reagent_usage", "dispensed_by")
    op.drop_column("experiment_reagent_usage", "shortage_qty")
    op.drop_column("experiment_reagent_usage", "outbound_status")
    op.drop_table("experiment_record_participant")
