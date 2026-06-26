"""complete T1.6A attachment schema

Revision ID: 202606250003
Revises: 202606250002
Create Date: 2026-06-25
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202606250003"
down_revision: str | None = "202606250002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


BIGINT_ID = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.execute("DELETE FROM attachment")
    op.drop_index("idx_attachment_entity", table_name="attachment")

    with op.batch_alter_table("attachment") as batch_op:
        batch_op.alter_column(
            "file_name",
            new_column_name="original_filename",
            existing_type=sa.String(length=255),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "sha256",
            new_column_name="checksum_sha256",
            existing_type=sa.String(length=64),
            existing_nullable=True,
            nullable=False,
        )
        batch_op.alter_column(
            "content_type_detected",
            new_column_name="content_type",
            existing_type=sa.String(length=100),
            type_=sa.String(length=120),
            existing_nullable=True,
            nullable=False,
        )
        batch_op.alter_column("file_size", existing_type=BIGINT_ID, existing_nullable=True, nullable=False)
        batch_op.add_column(sa.Column("project_id", BIGINT_ID, nullable=False))
        batch_op.add_column(sa.Column("storage_backend", sa.String(length=20), server_default="local", nullable=False))
        batch_op.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.create_foreign_key("fk_attachment_project_id_project", "project", ["project_id"], ["id"])
        batch_op.drop_column("file_type")
        batch_op.drop_column("thumbnail_key")
        batch_op.drop_column("upload_status")
        batch_op.drop_column("preview_status")

    op.create_index("idx_attachment_entity", "attachment", ["entity_type", "entity_id"])
    op.create_index("idx_attachment_active_entity", "attachment", ["entity_type", "entity_id", "deleted_at"])
    op.create_index("idx_attachment_project", "attachment", ["project_id"])


def downgrade() -> None:
    op.drop_index("idx_attachment_project", table_name="attachment")
    op.drop_index("idx_attachment_active_entity", table_name="attachment")
    op.drop_index("idx_attachment_entity", table_name="attachment")

    with op.batch_alter_table("attachment") as batch_op:
        batch_op.add_column(sa.Column("preview_status", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("upload_status", sa.String(length=20), server_default="uploaded", nullable=False))
        batch_op.add_column(sa.Column("thumbnail_key", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("file_type", sa.String(length=50), nullable=True))
        batch_op.drop_constraint("fk_attachment_project_id_project", type_="foreignkey")
        batch_op.drop_column("deleted_at")
        batch_op.drop_column("storage_backend")
        batch_op.drop_column("project_id")
        batch_op.alter_column("file_size", existing_type=BIGINT_ID, existing_nullable=False, nullable=True)
        batch_op.alter_column(
            "content_type",
            new_column_name="content_type_detected",
            existing_type=sa.String(length=120),
            type_=sa.String(length=100),
            existing_nullable=False,
            nullable=True,
        )
        batch_op.alter_column(
            "checksum_sha256",
            new_column_name="sha256",
            existing_type=sa.String(length=64),
            existing_nullable=False,
            nullable=True,
        )
        batch_op.alter_column(
            "original_filename",
            new_column_name="file_name",
            existing_type=sa.String(length=255),
            existing_nullable=False,
        )

    op.create_index("idx_attachment_entity", "attachment", ["entity_type", "entity_id"])
