"""add_uq_srcard_user_vocab

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2026-04-27 00:00:00.000000

"""
from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sr_cards") as batch_op:
        batch_op.create_unique_constraint(
            "uq_srcard_user_vocab", ["user_id", "vocab_item_id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("sr_cards") as batch_op:
        batch_op.drop_constraint("uq_srcard_user_vocab", type_="unique")
