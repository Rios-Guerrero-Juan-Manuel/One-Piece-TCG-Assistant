"""add deck version and match deck association

Revision ID: a467c8c204e8
Revises: 0001
Create Date: 2026-06-30 13:00:40.247074
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a467c8c204e8'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('decks') as batch_op:
            batch_op.add_column(
                sa.Column('version', sa.Integer(),
                          nullable=False, server_default='1')
            )
        with op.batch_alter_table('matches') as batch_op:
            batch_op.add_column(sa.Column('deck_id_self', sa.Text(), nullable=True))
            batch_op.add_column(sa.Column('deck_id_opp', sa.Text(), nullable=True))
    else:
        op.add_column(
            'decks',
            sa.Column('version', sa.Integer(),
                      nullable=False, server_default='1')
        )
        op.add_column('matches', sa.Column('deck_id_self', sa.Text(), nullable=True))
        op.add_column('matches', sa.Column('deck_id_opp', sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('matches') as batch_op:
            batch_op.drop_column('deck_id_opp')
            batch_op.drop_column('deck_id_self')
        with op.batch_alter_table('decks') as batch_op:
            batch_op.drop_column('version')
    else:
        op.drop_column('matches', 'deck_id_opp')
        op.drop_column('matches', 'deck_id_self')
        op.drop_column('decks', 'version')
