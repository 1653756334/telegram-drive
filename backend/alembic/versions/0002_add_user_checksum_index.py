from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_user_checksum_index"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite index to speed up dedup queries: WHERE user_id = ? AND checksum = ?
    op.create_index(
        "ix_files_user_checksum",
        "files",
        ["user_id", "checksum"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_files_user_checksum", table_name="files")

