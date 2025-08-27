from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "telegram_sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_string_encrypted", sa.String(8192), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "telegram_channels",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_id", sa.BigInteger, nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("user_id", "channel_id", name="uq_user_channel"),
    )

    op.create_table(
        "directories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("parent_id", sa.Integer, sa.ForeignKey("directories.id", ondelete="CASCADE"), nullable=True),
    )

    op.create_table(
        "files",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("directory_id", sa.Integer, sa.ForeignKey("directories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("size", sa.BigInteger, nullable=False),
        sa.Column("mime_type", sa.String(255), nullable=True),
        sa.Column("checksum", sa.String(255), nullable=True),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("telegram_channel_id", sa.BigInteger, nullable=False),
        sa.Column("telegram_message_id", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("user_id", "path", name="uq_user_path"),
    )


def downgrade() -> None:
    op.drop_table("files")
    op.drop_table("directories")
    op.drop_table("telegram_channels")
    op.drop_table("telegram_sessions")
    op.drop_table("users")

