from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_add_channel_username"
down_revision = "0002_add_user_checksum_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add username column to telegram_channels table
    op.add_column('telegram_channels', sa.Column('username', sa.String(255), nullable=True))


def downgrade() -> None:
    # Remove username column from telegram_channels table
    op.drop_column('telegram_channels', 'username')
