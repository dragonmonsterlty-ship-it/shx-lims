"""add data model tables

Revision ID: 202606220002
Revises: 202606220001
Create Date: 2026-06-22
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202606220002"
down_revision: str | None = "202606220001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


BIGINT_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
JSON_DATA = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def audit_columns() -> list[sa.Column]:
    return [
        sa.Column("created_by", BIGINT_ID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", BIGINT_ID, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    ]


def audit_foreign_keys() -> list[sa.ForeignKeyConstraint]:
    return [
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["user.id"]),
    ]


def upgrade() -> None:
    op.create_table(
        "attachment",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", BIGINT_ID, nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=50), nullable=True),
        sa.Column("content_type_detected", sa.String(length=100), nullable=True),
        sa.Column("file_size", BIGINT_ID, nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("thumbnail_key", sa.String(length=500), nullable=True),
        sa.Column("upload_status", sa.String(length=20), server_default="uploaded", nullable=False),
        sa.Column("preview_status", sa.String(length=20), nullable=True),
        sa.Column("uploaded_by", BIGINT_ID, nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by"], ["user.id"]),
    )
    op.create_index("idx_attachment_entity", "attachment", ["entity_type", "entity_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("table_name", sa.String(length=60), nullable=False),
        sa.Column("record_id", BIGINT_ID, nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column("business_action", sa.String(length=50), nullable=True),
        sa.Column("changed_by", BIGINT_ID, nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("changed_fields", JSON_DATA, nullable=True),
        sa.Column("old_value", JSON_DATA, nullable=True),
        sa.Column("new_value", JSON_DATA, nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.ForeignKeyConstraint(["changed_by"], ["user.id"]),
    )

    op.create_table(
        "project",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("project_code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("project_type", sa.String(length=50), nullable=True),
        sa.Column("lead_user_id", BIGINT_ID, nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *audit_columns(),
        sa.ForeignKeyConstraint(["lead_user_id"], ["user.id"]),
        *audit_foreign_keys(),
        sa.UniqueConstraint("project_code"),
    )
    op.create_index("idx_project_code", "project", ["project_code"])
    op.create_index("idx_project_status", "project", ["status"])

    op.create_table(
        "reagent",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("cas_no", sa.String(length=30), nullable=True),
        sa.Column("catalog_no", sa.String(length=80), nullable=True),
        sa.Column("manufacturer", sa.String(length=120), nullable=True),
        sa.Column("grade", sa.String(length=50), nullable=True),
        sa.Column("default_unit", sa.String(length=30), nullable=True),
        sa.Column("min_stock", sa.Numeric(18, 4), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *audit_columns(),
        *audit_foreign_keys(),
    )

    op.create_table(
        "test_method",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("method", sa.String(length=200), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("spec_lower", sa.Numeric(18, 6), nullable=True),
        sa.Column("spec_upper", sa.Numeric(18, 6), nullable=True),
        sa.Column("spec_text", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *audit_columns(),
        *audit_foreign_keys(),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "project_member",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("project_id", BIGINT_ID, nullable=False),
        sa.Column("user_id", BIGINT_ID, nullable=False),
        sa.Column("role_in_project", sa.String(length=20), server_default="member", nullable=False),
        *audit_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        *audit_foreign_keys(),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member_project_user"),
    )

    op.create_table(
        "reagent_lot",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("reagent_id", BIGINT_ID, nullable=False),
        sa.Column("lot_no", sa.String(length=80), nullable=False),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 4), server_default="0", nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("storage_condition", sa.String(length=100), nullable=True),
        sa.Column("opened_at", sa.Date(), nullable=True),
        sa.Column("controlled_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="in_stock", nullable=False),
        *audit_columns(),
        sa.ForeignKeyConstraint(["reagent_id"], ["reagent.id"]),
        *audit_foreign_keys(),
        sa.UniqueConstraint("reagent_id", "lot_no", name="uq_reagent_lot_reagent_lot_no"),
    )

    op.create_table(
        "sample",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("sample_code", sa.String(length=120), nullable=False),
        sa.Column("project_id", BIGINT_ID, nullable=False),
        sa.Column("compound_name", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("sample_type", sa.String(length=50), nullable=True),
        sa.Column("batch_no", sa.String(length=80), nullable=True),
        sa.Column("structure_smiles", sa.Text(), nullable=True),
        sa.Column("structure_molfile", sa.Text(), nullable=True),
        sa.Column("structure_image_key", sa.String(length=500), nullable=True),
        sa.Column("source", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("priority", sa.String(length=10), server_default="normal", nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *audit_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        *audit_foreign_keys(),
        sa.UniqueConstraint("sample_code"),
    )
    op.create_index("idx_sample_code", "sample", ["sample_code"])
    op.create_index("idx_sample_due_date", "sample", ["due_date"])
    op.create_index("idx_sample_project", "sample", ["project_id"])
    op.create_index("idx_sample_status", "sample", ["status"])

    op.create_table(
        "daily_log",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("user_id", BIGINT_ID, nullable=False),
        sa.Column("project_id", BIGINT_ID, nullable=True),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("related_sample_id", BIGINT_ID, nullable=True),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("reviewed_by", BIGINT_ID, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *audit_columns(),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.ForeignKeyConstraint(["related_sample_id"], ["sample.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        *audit_foreign_keys(),
    )
    op.create_index("idx_daily_log_project", "daily_log", ["project_id"])
    op.create_index("idx_daily_log_user_date", "daily_log", ["user_id", "log_date"])

    op.create_table(
        "experiment",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("project_id", BIGINT_ID, nullable=False),
        sa.Column("experiment_no", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("experiment_type", sa.String(length=50), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("author_id", BIGINT_ID, nullable=False),
        sa.Column("reviewer_id", BIGINT_ID, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("related_sample_id", BIGINT_ID, nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *audit_columns(),
        sa.ForeignKeyConstraint(["author_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"]),
        sa.ForeignKeyConstraint(["related_sample_id"], ["sample.id"]),
        sa.ForeignKeyConstraint(["reviewer_id"], ["user.id"]),
        *audit_foreign_keys(),
        sa.UniqueConstraint("experiment_no"),
    )
    op.create_index("idx_experiment_no", "experiment", ["experiment_no"])
    op.create_index("idx_experiment_project", "experiment", ["project_id"])
    op.create_index("idx_experiment_status", "experiment", ["status"])

    op.create_table(
        "inventory_txn",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("reagent_lot_id", BIGINT_ID, nullable=False),
        sa.Column("txn_type", sa.String(length=10), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("balance_after", sa.Numeric(18, 4), nullable=True),
        sa.Column("reference", sa.String(length=200), nullable=True),
        sa.Column("operator_id", BIGINT_ID, nullable=True),
        sa.Column("txn_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["operator_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["reagent_lot_id"], ["reagent_lot.id"]),
    )

    op.create_table(
        "sample_test",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("sample_id", BIGINT_ID, nullable=False),
        sa.Column("test_method_id", BIGINT_ID, nullable=False),
        sa.Column("assigned_to", BIGINT_ID, nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        *audit_columns(),
        sa.ForeignKeyConstraint(["assigned_to"], ["user.id"]),
        sa.ForeignKeyConstraint(["sample_id"], ["sample.id"]),
        sa.ForeignKeyConstraint(["test_method_id"], ["test_method.id"]),
        *audit_foreign_keys(),
        sa.UniqueConstraint("sample_id", "test_method_id", name="uq_sample_test_sample_method"),
    )

    op.create_table(
        "experiment_material",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("experiment_id", BIGINT_ID, nullable=False),
        sa.Column("material_name", sa.String(length=200), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("amount", sa.Numeric(18, 4), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("reagent_lot_id", BIGINT_ID, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *audit_columns(),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiment.id"]),
        sa.ForeignKeyConstraint(["reagent_lot_id"], ["reagent_lot.id"]),
        *audit_foreign_keys(),
    )

    op.create_table(
        "result",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("sample_test_id", BIGINT_ID, nullable=False),
        sa.Column("value_num", sa.Numeric(18, 6), nullable=True),
        sa.Column("value_text", sa.String(length=500), nullable=True),
        sa.Column("judgment", sa.String(length=10), nullable=True),
        sa.Column("entered_by", BIGINT_ID, nullable=True),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("reviewed_by", BIGINT_ID, nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        *audit_columns(),
        sa.ForeignKeyConstraint(["entered_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["sample_test_id"], ["sample_test.id"]),
        *audit_foreign_keys(),
        sa.UniqueConstraint("sample_test_id"),
    )


def downgrade() -> None:
    op.drop_table("result")
    op.drop_table("experiment_material")
    op.drop_table("sample_test")
    op.drop_table("inventory_txn")
    op.drop_index("idx_experiment_status", table_name="experiment")
    op.drop_index("idx_experiment_project", table_name="experiment")
    op.drop_index("idx_experiment_no", table_name="experiment")
    op.drop_table("experiment")
    op.drop_index("idx_daily_log_user_date", table_name="daily_log")
    op.drop_index("idx_daily_log_project", table_name="daily_log")
    op.drop_table("daily_log")
    op.drop_index("idx_sample_status", table_name="sample")
    op.drop_index("idx_sample_project", table_name="sample")
    op.drop_index("idx_sample_due_date", table_name="sample")
    op.drop_index("idx_sample_code", table_name="sample")
    op.drop_table("sample")
    op.drop_table("reagent_lot")
    op.drop_table("project_member")
    op.drop_table("test_method")
    op.drop_table("reagent")
    op.drop_index("idx_project_status", table_name="project")
    op.drop_index("idx_project_code", table_name="project")
    op.drop_table("project")
    op.drop_table("audit_log")
    op.drop_index("idx_attachment_entity", table_name="attachment")
    op.drop_table("attachment")
