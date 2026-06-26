"""add T1.6B audit log schema

Revision ID: 202606260001
Revises: 202606250003
Create Date: 2026-06-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "202606260001"
down_revision: str | None = "202606250003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


BIGINT_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
JSON_DATA = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.drop_table("audit_log")
    op.create_table(
        "audit_log",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("actor_user_id", BIGINT_ID, sa.ForeignKey("user.id"), nullable=True),
        sa.Column("actor_role", sa.String(length=20), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=False),
        sa.Column("entity_id", BIGINT_ID, nullable=False),
        sa.Column("project_id", BIGINT_ID, sa.ForeignKey("project.id"), nullable=True),
        sa.Column("target_user_id", BIGINT_ID, sa.ForeignKey("user.id"), nullable=True),
        sa.Column("before_data", JSON_DATA, nullable=True),
        sa.Column("after_data", JSON_DATA, nullable=True),
        sa.Column("metadata", JSON_DATA, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_audit_log_entity", "audit_log", ["entity_type", "entity_id"])
    op.create_index("idx_audit_log_project", "audit_log", ["project_id"])
    op.create_index("idx_audit_log_actor", "audit_log", ["actor_user_id"])
    op.create_index("idx_audit_log_action", "audit_log", ["action"])
    op.create_index("idx_audit_log_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_log_created_at", table_name="audit_log")
    op.drop_index("idx_audit_log_action", table_name="audit_log")
    op.drop_index("idx_audit_log_actor", table_name="audit_log")
    op.drop_index("idx_audit_log_project", table_name="audit_log")
    op.drop_index("idx_audit_log_entity", table_name="audit_log")
    op.drop_table("audit_log")
    op.create_table(
        "audit_log",
        sa.Column("id", BIGINT_ID, primary_key=True, autoincrement=True),
        sa.Column("table_name", sa.String(length=60), nullable=False),
        sa.Column("record_id", BIGINT_ID, nullable=False),
        sa.Column("action", sa.String(length=10), nullable=False),
        sa.Column("business_action", sa.String(length=50), nullable=True),
        sa.Column("changed_by", BIGINT_ID, sa.ForeignKey("user.id"), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("changed_fields", JSON_DATA, nullable=True),
        sa.Column("old_value", JSON_DATA, nullable=True),
        sa.Column("new_value", JSON_DATA, nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
    )
