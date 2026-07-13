"""add reference standard ledger

Revision ID: 202607130002
Revises: 202607130001
Create Date: 2026-07-13
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202607130002"
down_revision: str | None = "202607130001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ref_standard_code_counter",
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_value", sa.Integer(), nullable=False),
        sa.CheckConstraint("last_value >= 0", name="ck_ref_standard_code_counter_nonnegative"),
        sa.PrimaryKeyConstraint("year"),
    )
    op.create_table(
        "ref_standard",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("batch_no", sa.String(length=80), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("spec", sa.String(length=200), nullable=True),
        sa.Column("assigned_value", sa.Text(), nullable=True),
        sa.Column("initial_amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("current_amount", sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("storage_condition", sa.String(length=100), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="in_stock", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_by", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("source IN ('self_made', 'purchased')", name="ck_ref_standard_source"),
        sa.CheckConstraint("status IN ('in_stock', 'depleted', 'disposed')", name="ck_ref_standard_status"),
        sa.CheckConstraint("initial_amount > 0", name="ck_ref_standard_initial_amount_positive"),
        sa.CheckConstraint("current_amount >= 0", name="ck_ref_standard_current_amount_nonnegative"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_ref_standard_code"),
    )
    op.create_index("idx_ref_standard_code", "ref_standard", ["code"])
    op.create_index("idx_ref_standard_name", "ref_standard", ["name"])
    op.create_index("idx_ref_standard_batch_no", "ref_standard", ["batch_no"])
    op.create_index("idx_ref_standard_source", "ref_standard", ["source"])
    op.create_index("idx_ref_standard_status", "ref_standard", ["status"])
    op.create_index("idx_ref_standard_expires_at", "ref_standard", ["expires_at"])
    op.create_index("idx_ref_standard_is_deleted", "ref_standard", ["is_deleted"])

    with op.batch_alter_table("attachment") as batch_op:
        batch_op.alter_column("project_id", existing_type=sa.BigInteger(), nullable=True)


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM attachment WHERE entity_type = 'ref_standard'"))
    with op.batch_alter_table("attachment") as batch_op:
        batch_op.alter_column("project_id", existing_type=sa.BigInteger(), nullable=False)

    op.drop_index("idx_ref_standard_is_deleted", table_name="ref_standard")
    op.drop_index("idx_ref_standard_expires_at", table_name="ref_standard")
    op.drop_index("idx_ref_standard_status", table_name="ref_standard")
    op.drop_index("idx_ref_standard_source", table_name="ref_standard")
    op.drop_index("idx_ref_standard_batch_no", table_name="ref_standard")
    op.drop_index("idx_ref_standard_name", table_name="ref_standard")
    op.drop_index("idx_ref_standard_code", table_name="ref_standard")
    op.drop_table("ref_standard")
    op.drop_table("ref_standard_code_counter")
