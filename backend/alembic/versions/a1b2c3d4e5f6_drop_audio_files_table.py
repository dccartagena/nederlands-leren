"""drop_audio_files_table

Revision ID: a1b2c3d4e5f6
Revises: c3879087f590
Create Date: 2026-04-25 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = 'c3879087f590'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table('audio_files')


def downgrade() -> None:
    op.create_table(
        'audio_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vocab_item_id', sa.Integer(), nullable=True),
        sa.Column('sentence_text_nl', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('license', sa.String(length=50), nullable=True),
        sa.Column('speaker', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['vocab_item_id'], ['vocabulary_items.id']),
        sa.PrimaryKeyConstraint('id'),
    )
