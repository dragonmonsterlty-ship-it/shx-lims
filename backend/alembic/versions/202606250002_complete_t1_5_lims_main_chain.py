"""complete T1.5 LIMS main chain

Revision ID: 202606250002
Revises: 202606250001
Create Date: 2026-06-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202606250002"
down_revision: str | None = "202606250001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sample", sa.Column("amount", sa.Numeric(18, 4), nullable=True))
    op.add_column("sample", sa.Column("unit", sa.String(length=30), nullable=True))
    op.add_column("sample", sa.Column("storage_condition", sa.String(length=100), nullable=True))

    op.add_column("test_method", sa.Column("category", sa.String(length=50), nullable=True))
    op.add_column("test_method", sa.Column("version", sa.String(length=30), nullable=True))
    op.add_column("test_method", sa.Column("description", sa.Text(), nullable=True))

    op.add_column(
        "sample_test",
        sa.Column("priority", sa.String(length=10), server_default="normal", nullable=False),
    )
    op.add_column("sample_test", sa.Column("due_date", sa.Date(), nullable=True))
    op.create_index("idx_sample_test_assignee", "sample_test", ["assigned_to"])
    op.create_index("idx_sample_test_status", "sample_test", ["status"])

    op.add_column("result", sa.Column("result_data", sa.JSON(), nullable=True))
    op.add_column("result", sa.Column("conclusion", sa.Text(), nullable=True))
    op.add_column(
        "result",
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
    )
    op.add_column("result", sa.Column("submitted_by", sa.BigInteger(), nullable=True))
    op.add_column("result", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))
    with op.batch_alter_table("result") as batch_op:
        batch_op.create_foreign_key("fk_result_submitted_by_user", "user", ["submitted_by"], ["id"])
    op.create_index("idx_result_status", "result", ["status"])

    op.execute(
        "UPDATE result SET status = CASE "
        "WHEN review_status = 'approved' THEN 'approved' "
        "WHEN review_status = 'rejected' THEN 'rejected' "
        "ELSE 'draft' END"
    )


def downgrade() -> None:
    op.drop_index("idx_result_status", table_name="result")
    with op.batch_alter_table("result") as batch_op:
        batch_op.drop_constraint("fk_result_submitted_by_user", type_="foreignkey")
    op.drop_column("result", "submitted_at")
    op.drop_column("result", "submitted_by")
    op.drop_column("result", "status")
    op.drop_column("result", "conclusion")
    op.drop_column("result", "result_data")

    op.drop_index("idx_sample_test_status", table_name="sample_test")
    op.drop_index("idx_sample_test_assignee", table_name="sample_test")
    op.drop_column("sample_test", "due_date")
    op.drop_column("sample_test", "priority")

    op.drop_column("test_method", "description")
    op.drop_column("test_method", "version")
    op.drop_column("test_method", "category")

    op.drop_column("sample", "storage_condition")
    op.drop_column("sample", "unit")
    op.drop_column("sample", "amount")
