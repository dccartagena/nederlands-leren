"""add_review_logs_and_provenance

Adds the ReviewLog table (FSRS optimizer training data) and the
curate-first pipeline fields: frequency/CEFR/IPA/contrast/cloze on
vocabulary plus source/license/attribution/validated provenance on all
content models.

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2026-06-10

"""
from alembic import op
import sqlalchemy as sa


revision = 'd4e5f6a7b8c9'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def _add_provenance(table: str) -> None:
    op.add_column(table, sa.Column('source', sa.String(100)))
    op.add_column(table, sa.Column('source_license', sa.String(50)))
    op.add_column(table, sa.Column('attribution', sa.Text()))
    op.add_column(table, sa.Column('validated', sa.Boolean(), server_default=sa.false()))


def upgrade() -> None:
    op.create_table(
        'review_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('card_id', sa.Integer(), sa.ForeignKey('sr_cards.id'), nullable=False, index=True),
        sa.Column('vocab_item_id', sa.Integer(), sa.ForeignKey('vocabulary_items.id'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('state_before', sa.Integer(), nullable=False),
        sa.Column('state_after', sa.Integer(), nullable=False),
        sa.Column('stability_before', sa.Float()),
        sa.Column('stability_after', sa.Float()),
        sa.Column('difficulty_after', sa.Float()),
        sa.Column('elapsed_days', sa.Integer(), server_default='0'),
        sa.Column('reviewed_at', sa.DateTime(), index=True),
    )

    op.add_column('vocabulary_items', sa.Column('frequency_zipf', sa.Float()))
    op.add_column('vocabulary_items', sa.Column('cefr_level', sa.String(5)))
    op.add_column('vocabulary_items', sa.Column('ipa', sa.String(100)))
    op.add_column('vocabulary_items', sa.Column('contrast_note_es', sa.Text()))
    op.add_column('vocabulary_items', sa.Column('cloze_sentences_json', sa.JSON()))
    _add_provenance('vocabulary_items')

    _add_provenance('grammar_topics')

    op.add_column('stories', sa.Column('new_words_json', sa.JSON()))
    _add_provenance('stories')


def downgrade() -> None:
    op.drop_table('review_logs')
    for col in ('frequency_zipf', 'cefr_level', 'ipa', 'contrast_note_es',
                'cloze_sentences_json', 'source', 'source_license', 'attribution', 'validated'):
        op.drop_column('vocabulary_items', col)
    for col in ('source', 'source_license', 'attribution', 'validated'):
        op.drop_column('grammar_topics', col)
    for col in ('new_words_json', 'source', 'source_license', 'attribution', 'validated'):
        op.drop_column('stories', col)
