"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-29
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cards",
        sa.Column("card_id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("cost", sa.Integer, nullable=True),
        sa.Column("power", sa.Integer, nullable=True),
        sa.Column("counter", sa.Integer, nullable=False, server_default="0"),
        sa.Column("type", sa.Text, nullable=False),
        sa.Column("color", sa.JSON, nullable=True),
        sa.Column("traits", sa.JSON, nullable=True),
        sa.Column("attribute", sa.Text, nullable=True),
        sa.Column("keywords", sa.JSON, nullable=True),
        sa.Column("roles", sa.JSON, nullable=True),
        sa.Column("effect", sa.Text, nullable=True),
        sa.Column("effect_flags", sa.JSON, nullable=True),
        sa.Column("life", sa.Integer, nullable=True),
        sa.Column("set_id", sa.Text, nullable=True),
        sa.Column("set_name", sa.Text, nullable=True),
        sa.Column("rarity", sa.Text, nullable=True),
        sa.Column("image_url", sa.Text, nullable=True),
        sa.Column("unlimited_copies", sa.Boolean, server_default=sa.text("0")),
        sa.Column("language", sa.Text, server_default="'en'"),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "collection",
        sa.Column("card_id", sa.Text, sa.ForeignKey("cards.card_id"), primary_key=True),
        sa.Column("owned", sa.Integer, server_default="0"),
    )

    op.create_table(
        "decks",
        sa.Column("deck_id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("leader_card_id", sa.Text, nullable=False),
        sa.Column("source", sa.Text, nullable=True),
        sa.Column("event", sa.Text, nullable=True),
        sa.Column("date", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "deck_cards",
        sa.Column("deck_id", sa.Text, sa.ForeignKey("decks.deck_id"), primary_key=True),
        sa.Column("card_id", sa.Text, sa.ForeignKey("cards.card_id"), primary_key=True),
        sa.Column("qty", sa.Integer, nullable=False),
    )

    op.create_table(
        "matches",
        sa.Column("match_id", sa.Text, primary_key=True),
        sa.Column("room_id", sa.Text, nullable=True),
        sa.Column("version", sa.Text, nullable=True),
        sa.Column("source_file", sa.Text, nullable=False),
        sa.Column("leader_self", sa.Text, nullable=True),
        sa.Column("leader_opp", sa.Text, nullable=True),
        sa.Column("opponent_user", sa.Text, nullable=True),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("duration_turns", sa.Integer, nullable=True),
        sa.Column("played_at", sa.Text, nullable=True),
        sa.Column("imported_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "match_turns",
        sa.Column("match_id", sa.Text, sa.ForeignKey("matches.match_id"), primary_key=True),
        sa.Column("turn_no", sa.Integer, primary_key=True),
        sa.Column("player_idx", sa.Integer, nullable=False),
        sa.Column("don_drawn", sa.Integer, nullable=True),
        sa.Column("don_unused", sa.Integer, nullable=True),
        sa.Column("cards_played", sa.JSON, nullable=True),
        sa.Column("attacks", sa.JSON, nullable=True),
        sa.Column("counters", sa.JSON, nullable=True),
        sa.Column("errors", sa.JSON, nullable=True),
        sa.Column("state_end", sa.JSON, nullable=True),
    )

    op.create_table(
        "match_stats",
        sa.Column("match_id", sa.Text, sa.ForeignKey("matches.match_id"), primary_key=True),
        sa.Column("stats", sa.JSON, nullable=True),
    )

    op.create_table(
        "patterns",
        sa.Column("pattern_id", sa.Text, primary_key=True),
        sa.Column("filter", sa.JSON, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("severity", sa.Text, nullable=True),
        sa.Column("detected_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "recommendations",
        sa.Column("rec_id", sa.Text, primary_key=True),
        sa.Column("deck_id", sa.Text, sa.ForeignKey("decks.deck_id"), nullable=True),
        sa.Column("type", sa.Text, nullable=True),
        sa.Column("changes", sa.JSON, nullable=True),
        sa.Column("score", sa.Integer, nullable=True),
        sa.Column("rationale_payload", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "insights",
        sa.Column("doc_id", sa.Text, primary_key=True),
        sa.Column("source", sa.Text, nullable=True),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("type", sa.Text, nullable=True),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("hash", sa.Text, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.Text, primary_key=True),
        sa.Column("value", sa.Text, nullable=True),
    )

    op.create_table(
        "formats",
        sa.Column("format_name", sa.Text, primary_key=True),
        sa.Column("banned_cards", sa.JSON, nullable=True),
        sa.Column("banned_sets", sa.JSON, nullable=True),
        sa.Column("banned_blocks", sa.JSON, nullable=True),
        sa.Column("banned_pair1", sa.JSON, nullable=True),
        sa.Column("banned_pair2", sa.JSON, nullable=True),
    )

    op.create_table(
        "meta_snapshot",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("snapshot", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "deck_scores",
        sa.Column("deck_id", sa.Text, sa.ForeignKey("decks.deck_id"), primary_key=True),
        sa.Column("overall", sa.Integer, nullable=True),
        sa.Column("breakdown", sa.JSON, nullable=True),
        sa.Column("version", sa.Integer, server_default="0"),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    for table in [
        "deck_scores", "meta_snapshot", "formats", "settings",
        "insights", "recommendations",
        "patterns", "match_stats", "match_turns",
        "matches", "deck_cards", "decks", "collection", "cards",
    ]:
        op.drop_table(table)
