"""add daily report foundation

Revision ID: 202606230004
Revises: 202606230003
Create Date: 2026-06-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202606230004"
down_revision: str | None = "202606230003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def audit_columns() -> list[sa.Column]:
    return [
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    ]


def audit_foreign_keys() -> list[sa.ForeignKeyConstraint]:
    return [
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["user.id"]),
    ]


def upgrade() -> None:
    op.create_table(
        "daily_report",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("report_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("issues", sa.Text(), nullable=True),
        sa.Column("next_plan", sa.Text(), nullable=True),
        sa.Column("reviewer_id", sa.BigInteger(), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        *audit_columns(),
        sa.ForeignKeyConstraint(["reviewer_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        *audit_foreign_keys(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_daily_report_date", "daily_report", ["report_date"], unique=False)
    op.create_index("idx_daily_report_status", "daily_report", ["status"], unique=False)
    op.create_index("idx_daily_report_user_date", "daily_report", ["user_id", "report_date"], unique=False)

    op.create_table(
        "daily_report_item",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("daily_report_id", sa.BigInteger(), nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=True),
        sa.Column("experiment_record_id", sa.BigInteger(), nullable=True),
        sa.Column("work_type", sa.String(length=30), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("progress_note", sa.Text(), nullable=True),
        sa.Column("hours_spent", sa.Numeric(8, 2), nullable=True),
        sa.Column("problem_note", sa.Text(), nullable=True),
        sa.Column("next_step", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        *audit_columns(),
        sa.ForeignKeyConstraint(["daily_report_id"], ["daily_report.id"]),
        sa.ForeignKeyConstraint(["experiment_record_id"], ["experiment_record.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        *audit_foreign_keys(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_daily_report_item_experiment_record", "daily_report_item", ["experiment_record_id"], unique=False)
    op.create_index("idx_daily_report_item_project", "daily_report_item", ["project_id"], unique=False)
    op.create_index("idx_daily_report_item_report", "daily_report_item", ["daily_report_id"], unique=False)

    op.create_table(
        "daily_report_attachment",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("daily_report_id", sa.BigInteger(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=True),
        sa.Column("storage_path", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=True),
        *audit_columns(),
        sa.ForeignKeyConstraint(["daily_report_id"], ["daily_report.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["user.id"]),
        *audit_foreign_keys(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_daily_report_attachment_report", "daily_report_attachment", ["daily_report_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_daily_report_attachment_report", table_name="daily_report_attachment")
    op.drop_table("daily_report_attachment")
    op.drop_index("idx_daily_report_item_report", table_name="daily_report_item")
    op.drop_index("idx_daily_report_item_project", table_name="daily_report_item")
    op.drop_index("idx_daily_report_item_experiment_record", table_name="daily_report_item")
    op.drop_table("daily_report_item")
    op.drop_index("idx_daily_report_user_date", table_name="daily_report")
    op.drop_index("idx_daily_report_status", table_name="daily_report")
    op.drop_index("idx_daily_report_date", table_name="daily_report")
    op.drop_table("daily_report")
