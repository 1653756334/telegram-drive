from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0004_redesign_file_structure"
down_revision = "0003_add_channel_username"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Since we're not preserving data, drop all tables and recreate
    op.execute("DROP TABLE IF EXISTS files CASCADE")
    op.execute("DROP TABLE IF EXISTS directories CASCADE")
    op.execute("DROP TABLE IF EXISTS telegram_sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS telegram_channels CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")

    # Recreate all tables with new structure
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'))
    )

    op.create_table('telegram_sessions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_string_encrypted', sa.String(8192), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True)
    )

    op.create_table('telegram_channels',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('channel_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )

    op.create_unique_constraint('uq_user_channel', 'telegram_channels', ['user_id', 'channel_id'])

    # Create unified nodes table (simplified without ltree for now)
    op.create_table('nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('nodes.id', ondelete='RESTRICT'), nullable=True),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('kind', sa.Text(), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),  # Use TEXT instead of LTREE for simplicity
        sa.Column('depth', sa.Integer(), nullable=True),
        sa.Column('sort_key', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('mime_type', sa.String(255), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('telegram_channel_id', sa.BigInteger(), nullable=True),
        sa.Column('telegram_message_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("kind IN ('folder', 'file')", name='check_node_kind')
    )

    # Create indexes
    # Unique constraint: same name under same parent (excluding deleted)
    op.create_index('uniq_live_name_per_parent', 'nodes', ['user_id', 'parent_id', sa.text('lower(name)')],
                   unique=True, postgresql_where=sa.text('deleted_at IS NULL'))

    # Index for listing children
    op.create_index('idx_nodes_parent', 'nodes', ['parent_id'],
                   postgresql_where=sa.text('deleted_at IS NULL'))

    # Index for path-based queries
    op.create_index('idx_nodes_path', 'nodes', ['path'])

    # Index for checksum-based deduplication
    op.create_index('idx_nodes_user_checksum', 'nodes', ['user_id', 'checksum'],
                   postgresql_where=sa.text('checksum IS NOT NULL AND deleted_at IS NULL'))


def downgrade() -> None:
    # This is a destructive migration, downgrade not recommended
    # But we'll provide basic structure restoration
    
    op.drop_table('nodes')
    
    # Recreate old users table structure
    op.drop_table('users')
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('username', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )
    
    # Recreate old directories table
    op.create_table('directories',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('directories.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )
    
    # Recreate old files table
    op.create_table('files',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('directory_id', sa.Integer(), sa.ForeignKey('directories.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(255), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('path', sa.String(1000), nullable=False),
        sa.Column('telegram_channel_id', sa.BigInteger(), nullable=False),
        sa.Column('telegram_message_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()'))
    )
