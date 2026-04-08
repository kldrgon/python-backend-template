"""pre_domain

Revision ID: pre_domain
Revises: framework_outbox
Create Date: 2026-04-08 00:00:00

"""

from alembic import op  # pyright: ignore[reportMissingImports]
import sqlalchemy as sa


revision = "pre_domain"
down_revision = "framework_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("nickname", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("org_name", sa.String(length=255), nullable=True),
        sa.Column("bio", sa.String(length=1000), nullable=True),
        sa.Column("avatar", sa.String(length=512), nullable=True),
        sa.Column("location", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("nickname"),
        sa.UniqueConstraint("phone", name="uq_user_phone"),
    )
    op.create_index(op.f("ix_user_phone"), "user", ["phone"], unique=False)
    op.create_index(op.f("ix_user_user_id"), "user", ["user_id"], unique=True)

    op.create_table(
        "user_linked_account",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_account_id", sa.String(length=255), nullable=False),
        sa.Column("access_token", sa.String(length=2048), nullable=True),
        sa.Column("refresh_token", sa.String(length=2048), nullable=True),
        sa.Column("expires_at", sa.Integer(), nullable=True),
        sa.Column("token_type", sa.String(length=64), nullable=True),
        sa.Column("scope", sa.String(length=1024), nullable=True),
        sa.Column("id_token", sa.String(length=4096), nullable=True),
        sa.Column("raw_data", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider",
            "provider_account_id",
            name="uq_linked_account_provider_account",
        ),
    )
    op.create_index(
        "ix_user_linked_account_provider",
        "user_linked_account",
        ["provider"],
        unique=False,
    )
    op.create_index(
        "ix_user_linked_account_provider_account_id",
        "user_linked_account",
        ["provider_account_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_linked_account_user_id",
        "user_linked_account",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "user_role",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role", name="uq_user_role_user_id_role"),
    )
    op.create_index(op.f("ix_user_role_role"), "user_role", ["role"], unique=False)
    op.create_index(op.f("ix_user_role_user_id"), "user_role", ["user_id"], unique=False)

    op.create_table(
        "storage_locator",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("storage_locator_id", sa.String(length=36), nullable=False),
        sa.Column("storage_provider", sa.String(length=255), nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("region", sa.String(length=255), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_locator_id", name="uq_storage_locator_id"),
    )
    op.create_index(
        "ix_storage_locator_provider_bucket",
        "storage_locator",
        ["storage_provider", "bucket"],
        unique=False,
    )
    op.create_index("ix_storage_locator_sha256", "storage_locator", ["sha256"], unique=False)
    op.create_index(
        op.f("ix_storage_locator_storage_locator_id"),
        "storage_locator",
        ["storage_locator_id"],
        unique=True,
    )

    op.create_table(
        "blob",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("blob_id", sa.String(length=36), nullable=False),
        sa.Column("blob_sha256", sa.String(length=64), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("storage_locator_id", sa.Integer(), nullable=True),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("storage_class", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["storage_locator_id"], ["storage_locator.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_blob_blob_id"), "blob", ["blob_id"], unique=True)
    op.create_index("ix_blob_created_at", "blob", ["created_at"], unique=False)
    op.create_index("ix_blob_kind", "blob", ["kind"], unique=False)
    op.create_index("ix_blob_sha256", "blob", ["blob_sha256"], unique=False)
    op.create_index(op.f("ix_blob_status"), "blob", ["status"], unique=False)
    op.create_index(op.f("ix_blob_storage_locator_id"), "blob", ["storage_locator_id"], unique=False)

    op.create_table(
        "blob_reference",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ref_id", sa.String(length=36), nullable=False),
        sa.Column("blob_id", sa.String(length=36), nullable=False),
        sa.Column("owner_type", sa.String(length=64), nullable=False),
        sa.Column("owner_id", sa.String(length=64), nullable=False),
        sa.Column("edge_key", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "owner_type",
            "owner_id",
            "edge_key",
            name="uq_blob_reference_owner_edge",
        ),
    )
    op.create_index("ix_blob_reference_blob_id", "blob_reference", ["blob_id"], unique=False)
    op.create_index("ix_blob_reference_owner", "blob_reference", ["owner_type", "owner_id"], unique=False)
    op.create_index("ix_blob_reference_ref_id", "blob_reference", ["ref_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_blob_reference_ref_id", table_name="blob_reference")
    op.drop_index("ix_blob_reference_owner", table_name="blob_reference")
    op.drop_index("ix_blob_reference_blob_id", table_name="blob_reference")
    op.drop_table("blob_reference")

    op.drop_index(op.f("ix_blob_storage_locator_id"), table_name="blob")
    op.drop_index(op.f("ix_blob_status"), table_name="blob")
    op.drop_index("ix_blob_sha256", table_name="blob")
    op.drop_index("ix_blob_kind", table_name="blob")
    op.drop_index("ix_blob_created_at", table_name="blob")
    op.drop_index(op.f("ix_blob_blob_id"), table_name="blob")
    op.drop_table("blob")

    op.drop_index(op.f("ix_storage_locator_storage_locator_id"), table_name="storage_locator")
    op.drop_index("ix_storage_locator_sha256", table_name="storage_locator")
    op.drop_index("ix_storage_locator_provider_bucket", table_name="storage_locator")
    op.drop_table("storage_locator")

    op.drop_index(op.f("ix_user_role_user_id"), table_name="user_role")
    op.drop_index(op.f("ix_user_role_role"), table_name="user_role")
    op.drop_table("user_role")

    op.drop_index("ix_user_linked_account_user_id", table_name="user_linked_account")
    op.drop_index("ix_user_linked_account_provider_account_id", table_name="user_linked_account")
    op.drop_index("ix_user_linked_account_provider", table_name="user_linked_account")
    op.drop_table("user_linked_account")

    op.drop_index(op.f("ix_user_user_id"), table_name="user")
    op.drop_index(op.f("ix_user_phone"), table_name="user")
    op.drop_table("user")
