"""add self_player_idx to matches

Revision ID: b3f2a1c907d4
Revises: a467c8c204e8
Create Date: 2026-06-30 14:50:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b3f2a1c907d4'
down_revision: str | None = 'a467c8c204e8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('matches') as batch_op:
            batch_op.add_column(
                sa.Column('self_player_idx', sa.Integer(), nullable=True)
            )
    else:
        op.add_column(
            'matches',
            sa.Column('self_player_idx', sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'sqlite':
        with op.batch_alter_table('matches') as batch_op:
            batch_op.drop_column('self_player_idx')
    else:
        op.drop_column('matches', 'self_player_idx')
