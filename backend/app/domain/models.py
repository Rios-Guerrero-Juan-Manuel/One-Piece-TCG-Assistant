from dataclasses import dataclass


@dataclass
class Card:
    card_id: str
    name: str
    cost: int | None
    power: int | None
    counter: int
    type: str
    color: list[str]
    traits: list[str]
    attribute: str | None
    keywords: list[str]
    roles: list[str]
    effect: str
    life: int | None
    set_id: str
    set_name: str
    rarity: str
    image_url: str
    unlimited_copies: bool


@dataclass
class Deck:
    deck_id: str
    name: str
    leader_card_id: str
    source: str | None
    event: str | None
    date: str | None
    cards: list[tuple[str, int]]


@dataclass
class Player:
    user: str
    leader_card_id: str
    goes_first: bool
    is_self: bool


@dataclass
class Action:
    type: str
    actor: str | None = None
    card_id: str | None = None
    target_card_id: str | None = None
    target_instance_id: str | None = None
    cost: int | None = None
    power: int | None = None
    counter_value: int | None = None
    amount: int | None = None
    effect_text: str | None = None
    result: str | None = None


@dataclass
class Turn:
    turn_no: int
    player_idx: int
    don_drawn: int
    don_available: int
    don_unused_at_end: int
    actions: list[Action]
    errors: list[str]
    state_end: dict


@dataclass
class Match:
    match_id: str
    room_id: str | None
    version: str | None
    source_file: str
    players: list[Player]
    turns: list[Turn]
    winner_idx: int | None
    reason: str | None
    duration_turns: int | None
    deck_id_self: str | None = None


@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]


@dataclass
class DeckScore:
    deck_id: str
    overall: int
    breakdown: dict[str, int]
    version: int


@dataclass
class Recommendation:
    card_out: str | None
    card_in: str
    qty: int
    score: int
    rationale_payload: dict
