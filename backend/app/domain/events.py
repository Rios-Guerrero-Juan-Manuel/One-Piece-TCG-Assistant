from dataclasses import dataclass


@dataclass
class CardsRefreshed:
    new_count: int
    updated_count: int


@dataclass
class DeckUpdated:
    deck_id: str


@dataclass
class DeckImported:
    deck_id: str


@dataclass
class MatchImported:
    match_id: str


@dataclass
class PatternsDetected:
    pattern_count: int


@dataclass
class StatsComputed:
    match_count: int


@dataclass
class CollectionUpdated:
    card_id: str


@dataclass
class SettingsChanged:
    key: str
    value: str
