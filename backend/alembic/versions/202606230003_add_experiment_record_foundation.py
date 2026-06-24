"""add experiment record foundation

Revision ID: 202606230003
Revises: 202606230002
Create Date: 2026-06-23
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202606230003"
down_revision: str | None = "202606230002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiment_record",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("record_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("creator_id", sa.BigInteger(), nullable=False),
        sa.Column("owner_id", sa.BigInteger(), nullable=True),
        sa.Column("experiment_date", sa.Date(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("procedure", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("next_step", sa.Text(), nullable=True),
        sa.Column("risk_note", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["creator_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("idx_experiment_record_date", "experiment_record", ["experiment_date"], unique=False)
    op.create_index("idx_experiment_record_project", "experiment_record", ["project_id"], unique=False)
    op.create_index("idx_experiment_record_status", "experiment_record", ["status"], unique=False)
    op.create_index("idx_experiment_record_type", "experiment_record", ["record_type"], unique=False)

    op.create_table(
        "experiment_reagent_usage",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("experiment_record_id", sa.BigInteger(), nullable=False),
        sa.Column("reagent_id", sa.BigInteger(), nullable=True),
        sa.Column("lot_id", sa.BigInteger(), nullable=True),
        sa.Column("reagent_name_snapshot", sa.String(length=200), nullable=True),
        sa.Column("lot_code_snapshot", sa.String(length=80), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("purpose", sa.String(length=200), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["experiment_record_id"], ["experiment_record.id"]),
        sa.ForeignKeyConstraint(["lot_id"], ["reagent_lot.id"]),
        sa.ForeignKeyConstraint(["reagent_id"], ["reagent.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_experiment_reagent_usage_record", "experiment_reagent_usage", ["experiment_record_id"], unique=False)

    op.create_table(
        "experiment_attachment",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("experiment_record_id", sa.BigInteger(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=True),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.BigInteger(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["experiment_record_id"], ["experiment_record.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_experiment_attachment_record", "experiment_attachment", ["experiment_record_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_experiment_attachment_record", table_name="experiment_attachment")
    op.drop_table("experiment_attachment")
    op.drop_index("idx_experiment_reagent_usage_record", table_name="experiment_reagent_usage")
    op.drop_table("experiment_reagent_usage")
    op.drop_index("idx_experiment_record_type", table_name="experiment_record")
    op.drop_index("idx_experiment_record_status", table_name="experiment_record")
    op.drop_index("idx_experiment_record_project", table_name="experiment_record")
    op.drop_index("idx_experiment_record_date", table_name="experiment_record")
    op.drop_table("experiment_record")
