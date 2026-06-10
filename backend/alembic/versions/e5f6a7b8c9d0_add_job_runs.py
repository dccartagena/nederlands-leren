"""add_job_runs

Background scheduler bookkeeping: latest run of each maintenance job.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-10

"""
from alembic import op
import sqlalchemy as sa


revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'job_runs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('job_name', sa.String(50), nullable=False, unique=True, index=True),
        sa.Column('last_run_at', sa.DateTime()),
        sa.Column('last_status', sa.String(10)),
        sa.Column('detail', sa.Text()),
        sa.Column('duration_ms', sa.Integer()),
    )


def downgrade() -> None:
    op.drop_table('job_runs')
