"""add card_prices table

Revision ID: f8a1c3d5e7b9
Revises: b3f2a1c907d4
Create Date: 2026-07-01 15:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'f8a1c3d5e7b9'
down_revision: str | None = 'b3f2a1c907d4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'card_prices',
        sa.Column('card_id', sa.Text(), nullable=False),
        sa.Column('trend_price', sa.Float(), nullable=True),
        sa.Column('avg_price', sa.Float(), nullable=True),
        sa.Column('low_price', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('card_id'),
    )


def downgrade() -> None:
    op.drop_table('card_prices')
