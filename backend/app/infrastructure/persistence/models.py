import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CardORM(Base):
    __tablename__ = "cards"

    card_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    power: Mapped[int | None] = mapped_column(Integer, nullable=True)
    counter: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(Text)
    color: Mapped[list] = mapped_column(JSON)
    traits: Mapped[list] = mapped_column(JSON)
    attribute: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list] = mapped_column(JSON)
    roles: Mapped[list] = mapped_column(JSON)
    effect: Mapped[str] = mapped_column(Text)
    effect_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    life: Mapped[int | None] = mapped_column(Integer, nullable=True)
    set_id: Mapped[str] = mapped_column(Text)
    set_name: Mapped[str] = mapped_column(Text)
    rarity: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(Text)
    unlimited_copies: Mapped[bool] = mapped_column(Boolean, default=False)
    language: Mapped[str] = mapped_column(Text, default="en")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )


class CollectionORM(Base):
    __tablename__ = "collection"

    card_id: Mapped[str] = mapped_column(Text, ForeignKey("cards.card_id"), primary_key=True)
    owned: Mapped[int] = mapped_column(Integer, default=0)


class DeckORM(Base):
    __tablename__ = "decks"

    deck_id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    leader_card_id: Mapped[str] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(Text, nullable=True)
    event: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )


class DeckCardORM(Base):
    __tablename__ = "deck_cards"

    deck_id: Mapped[str] = mapped_column(Text, ForeignKey("decks.deck_id"), primary_key=True)
    card_id: Mapped[str] = mapped_column(Text, ForeignKey("cards.card_id"), primary_key=True)
    qty: Mapped[int] = mapped_column(Integer)


class MatchORM(Base):
    __tablename__ = "matches"

    match_id: Mapped[str] = mapped_column(Text, primary_key=True)
    room_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file: Mapped[str] = mapped_column(Text)
    leader_self: Mapped[str] = mapped_column(Text)
    leader_opp: Mapped[str] = mapped_column(Text)
    opponent_user: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_turns: Mapped[int | None] = mapped_column(Integer, nullable=True)
    played_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    imported_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
    deck_id_self: Mapped[str | None] = mapped_column(Text, nullable=True)
    deck_id_opp: Mapped[str | None] = mapped_column(Text, nullable=True)
    self_player_idx: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MatchTurnORM(Base):
    __tablename__ = "match_turns"

    match_id: Mapped[str] = mapped_column(Text, ForeignKey("matches.match_id"), primary_key=True)
    turn_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_idx: Mapped[int] = mapped_column(Integer)
    don_drawn: Mapped[int] = mapped_column(Integer)
    don_unused: Mapped[int] = mapped_column(Integer)
    cards_played: Mapped[list] = mapped_column(JSON)
    attacks: Mapped[list] = mapped_column(JSON)
    counters: Mapped[list] = mapped_column(JSON)
    errors: Mapped[list] = mapped_column(JSON)
    state_end: Mapped[dict] = mapped_column(JSON)


class MatchStatsORM(Base):
    __tablename__ = "match_stats"

    match_id: Mapped[str] = mapped_column(Text, primary_key=True)
    stats: Mapped[dict] = mapped_column(JSON)


class PatternORM(Base):
    __tablename__ = "patterns"

    pattern_id: Mapped[str] = mapped_column(Text, primary_key=True)
    filter: Mapped[dict] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text)
    detected_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )


class RecommendationORM(Base):
    __tablename__ = "recommendations"

    rec_id: Mapped[str] = mapped_column(Text, primary_key=True)
    deck_id: Mapped[str] = mapped_column(Text, ForeignKey("decks.deck_id"))
    type: Mapped[str] = mapped_column(Text)
    changes: Mapped[list] = mapped_column(JSON)
    score: Mapped[int] = mapped_column(Integer)
    rationale_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )


class InsightORM(Base):
    __tablename__ = "insights"

    doc_id: Mapped[str] = mapped_column(Text, primary_key=True)
    source: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    hash: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )


class SettingsORM(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class FormatORM(Base):
    __tablename__ = "formats"

    format_name: Mapped[str] = mapped_column(Text, primary_key=True)
    banned_cards: Mapped[list] = mapped_column(JSON)
    banned_sets: Mapped[list] = mapped_column(JSON)
    banned_blocks: Mapped[list] = mapped_column(JSON)
    banned_pair1: Mapped[list] = mapped_column(JSON)
    banned_pair2: Mapped[list] = mapped_column(JSON)


class MetaSnapshotORM(Base):
    __tablename__ = "meta_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )


class DeckScoreORM(Base):
    __tablename__ = "deck_scores"

    deck_id: Mapped[str] = mapped_column(Text, ForeignKey("decks.deck_id"), primary_key=True)
    overall: Mapped[int] = mapped_column(Integer)
    breakdown: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )


class CardPriceORM(Base):
    __tablename__ = "card_prices"

    card_id: Mapped[str] = mapped_column(Text, primary_key=True)
    trend_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.UTC),
    )
