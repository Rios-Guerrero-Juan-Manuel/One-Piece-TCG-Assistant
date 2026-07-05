import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.application.event_bus import get_event_bus
from app.domain.engines.deck.rule_validator import RuleValidator
from app.domain.events import DeckImported
from app.domain.models import Card, Deck
from app.infrastructure.importers.deck_importer import DeckImporter
from app.infrastructure.persistence.models import CardORM
from app.infrastructure.persistence.repositories.deck_repo import DeckRepository
from app.infrastructure.persistence.repositories.format_repo import FormatRepository
from app.infrastructure.persistence.repositories.settings_repo import SettingsRepository
from app.infrastructure.persistence.session import get_db
from app.presentation.schemas.deck_schema import (
    CompleteDeckResponse,
    DeckCreateRequest,
    DeckCreateResponse,
    DeckDetailCardResponse,
    DeckDetailResponse,
    DeckImportRequest,
    DeckImportResponse,
    DeckListItemResponse,
    DeckListResponse,
    DeckScoreResponse,
    DeckVersionItem,
    DeckVersionsResponse,
    MissingCard,
    SubstitutionSuggestion,
    ValidationResultResponse,
)

router = APIRouter(prefix="/api/decks", tags=["decks"])


def _card_orm_to_domain(c: CardORM) -> Card:
    return Card(
        card_id=c.card_id,
        name=c.name,
        cost=c.cost,
        power=c.power,
        counter=c.counter,
        type=c.type,
        color=c.color or [],
        traits=c.traits or [],
        attribute=c.attribute,
        keywords=c.keywords or [],
        roles=c.roles or [],
        effect=c.effect,
        life=c.life,
        set_id=c.set_id,
        set_name=c.set_name,
        rarity=c.rarity,
        image_url=c.image_url,
        unlimited_copies=c.unlimited_copies,
    )


@router.get("", response_model=DeckListResponse)
async def list_decks(db: Session = Depends(get_db)):
    repo = DeckRepository(db)
    decks = repo.get_all()
    result = []
    for d in decks:
        _, deck_cards = repo.get_by_id(d.deck_id)
        card_count = sum(dc.qty for dc in deck_cards)
        result.append(
            DeckListItemResponse(
                deck_id=d.deck_id,
                name=d.name,
                leader_card_id=d.leader_card_id,
                source=d.source,
                card_count=card_count,
                version=d.version,
            )
        )
    return DeckListResponse(decks=result)


@router.get("/{deck_id}", response_model=DeckDetailResponse)
async def get_deck(deck_id: str, db: Session = Depends(get_db)):
    repo = DeckRepository(db)
    deck, deck_cards_orm = repo.get_by_id(deck_id)
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    card_ids = [dc.card_id for dc in deck_cards_orm]
    cards_orm = db.query(CardORM).filter(CardORM.card_id.in_(card_ids)).all() if card_ids else []
    card_map = {c.card_id: c for c in cards_orm}

    cards_response = []
    for dc in deck_cards_orm:
        c = card_map.get(dc.card_id)
        if c:
            cards_response.append(
                DeckDetailCardResponse(
                    card_id=c.card_id,
                    name=c.name,
                    cost=c.cost,
                    power=c.power,
                    counter=c.counter,
                    type=c.type,
                    color=c.color or [],
                    traits=c.traits or [],
                    keywords=c.keywords or [],
                    roles=c.roles or [],
                    effect=c.effect,
                    image_url=c.image_url,
                    set_id=c.set_id,
                    qty=dc.qty,
                )
            )

    return DeckDetailResponse(
        deck_id=deck.deck_id,
        name=deck.name,
        leader_card_id=deck.leader_card_id,
        source=deck.source,
        event=deck.event,
        date=deck.date,
        version=deck.version,
        cards=cards_response,
    )


@router.get("/leader/{leader_card_id}/versions", response_model=DeckVersionsResponse)
async def get_deck_versions(leader_card_id: str, db: Session = Depends(get_db)):
    """Get all versions of a deck for a given leader."""
    repo = DeckRepository(db)
    decks = repo.get_by_leader(leader_card_id)
    versions = []
    for d in decks:
        _, deck_cards = repo.get_by_id(d.deck_id)
        card_count = sum(dc.qty for dc in deck_cards)
        versions.append(
            DeckVersionItem(
                deck_id=d.deck_id,
                name=d.name,
                version=d.version,
                card_count=card_count,
                created_at=d.created_at.isoformat() if d.created_at else None,
            )
        )
    return DeckVersionsResponse(leader_card_id=leader_card_id, versions=versions)


@router.post("/import", response_model=DeckImportResponse)
async def import_deck(request: DeckImportRequest, db: Session = Depends(get_db)):
    leader_card_id, cards = DeckImporter.parse_deck_text(request.text)
    if not leader_card_id:
        raise HTTPException(
            status_code=400, detail="No leader card found in deck text"
        )

    repo = DeckRepository(db)

    if request.mode == "new_version":
        if request.leader_card_id:
            if request.leader_card_id != leader_card_id:
                raise HTTPException(
                    status_code=400,
                    detail="Leader card in deck text does not match the selected deck",
                )
            version_leader = request.leader_card_id
        else:
            version_leader = leader_card_id

        name = request.name
        if not name:
            existing = repo.get_by_leader(version_leader)
            if existing:
                name = re.sub(r"\s+v\d+$", "", existing[0].name)
        if not name:
            raise HTTPException(
                status_code=400,
                detail="Deck name is required for a new version",
            )
        deck = repo.create_new_version(version_leader, name, cards, request.source)
    else:
        deck_id = str(uuid.uuid4())
        deck_data = {
            "deck_id": deck_id,
            "name": request.name,
            "leader_card_id": leader_card_id,
            "source": request.source,
            "event": None,
            "date": None,
            "version": 1,
        }
        deck = repo.create(deck_data, cards)

    db.commit()
    get_event_bus().publish("DeckImported", DeckImported(deck_id=deck.deck_id))
    card_count = sum(qty for _, qty in cards)
    return DeckImportResponse(
        deck_id=deck.deck_id,
        name=deck.name,
        leader_card_id=leader_card_id,
        card_count=card_count,
        version=deck.version,
    )


@router.post("", response_model=DeckCreateResponse)
async def create_deck(request: DeckCreateRequest, db: Session = Depends(get_db)):
    deck_id = request.deck_id or str(uuid.uuid4())
    deck_data = {
        "deck_id": deck_id,
        "name": request.name,
        "leader_card_id": request.leader_card_id,
        "source": request.source,
        "event": None,
        "date": None,
        "version": 1,
    }
    cards = [(c.card_id, c.qty) for c in request.cards]
    repo = DeckRepository(db)
    repo.upsert(deck_data, cards)
    db.commit()
    get_event_bus().publish("DeckImported", DeckImported(deck_id=deck_id))
    card_count = sum(qty for _, qty in cards)
    return DeckCreateResponse(
        deck_id=deck_id,
        name=request.name,
        leader_card_id=request.leader_card_id,
        card_count=card_count,
    )


@router.delete("/{deck_id}")
async def delete_deck(deck_id: str, db: Session = Depends(get_db)):
    """Delete a deck. Match references to it are nullified (history preserved)."""
    repo = DeckRepository(db)
    deleted = repo.delete(deck_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Deck not found")
    db.commit()
    return {"deck_id": deck_id, "deleted": True}


@router.post("/{deck_id}/validate", response_model=ValidationResultResponse)
async def validate_deck(
    deck_id: str,
    format_name: str | None = None,
    db: Session = Depends(get_db),
):
    repo = DeckRepository(db)
    deck_orm, deck_cards_orm = repo.get_by_id(deck_id)
    if not deck_orm:
        raise HTTPException(status_code=404, detail="Deck not found")

    card_ids = {dc.card_id for dc in deck_cards_orm}
    card_ids.add(deck_orm.leader_card_id)
    cards_orm = (
        db.query(CardORM).filter(CardORM.card_id.in_(card_ids)).all()
        if card_ids else []
    )
    cards_dict = {c.card_id: _card_orm_to_domain(c) for c in cards_orm}

    domain_deck = Deck(
        deck_id=deck_orm.deck_id,
        name=deck_orm.name,
        leader_card_id=deck_orm.leader_card_id,
        source=deck_orm.source,
        event=deck_orm.event,
        date=deck_orm.date,
        cards=[(dc.card_id, dc.qty) for dc in deck_cards_orm],
    )

    format_bans = None
    fmt_name = format_name
    if not fmt_name:
        settings_repo = SettingsRepository(db)
        fmt_name = settings_repo.get("active_format")

    if fmt_name:
        fmt_repo = FormatRepository(db)
        fmt = fmt_repo.get_by_name(fmt_name)
        if fmt:
            format_bans = {
                "banned_cards": fmt.banned_cards or [],
                "banned_sets": fmt.banned_sets or [],
                "banned_blocks": fmt.banned_blocks or [],
                "banned_pair1": fmt.banned_pair1 or [],
                "banned_pair2": fmt.banned_pair2 or [],
            }

    validator = RuleValidator()
    result = validator.validate(domain_deck, cards_dict, format_bans)

    return ValidationResultResponse(
        errors=result.errors,
        warnings=result.warnings,
    )


@router.get("/{deck_id}/score", response_model=DeckScoreResponse)
async def get_deck_score(deck_id: str, db: Session = Depends(get_db)):
    from app.application.services.scoring_engine import ScoringEngine
    from app.infrastructure.persistence.session import SessionLocal

    engine = ScoringEngine(SessionLocal, auto_subscribe=False)
    try:
        score = engine.score_deck(deck_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Deck not found") from None
    return DeckScoreResponse(
        deck_id=score.deck_id,
        overall=score.overall,
        breakdown=score.breakdown,
        version=score.version,
    )


@router.post("/{deck_id}/complete", response_model=CompleteDeckResponse)
async def complete_deck(
    deck_id: str,
    format_name: str | None = None,
    db: Session = Depends(get_db),
):
    repo = DeckRepository(db)
    deck_orm, deck_cards_orm = repo.get_by_id(deck_id)
    if not deck_orm:
        raise HTTPException(status_code=404, detail="Deck not found")

    all_card_ids = {dc.card_id for dc in deck_cards_orm}
    all_card_ids.add(deck_orm.leader_card_id)
    cards_orm = (
        db.query(CardORM).filter(CardORM.card_id.in_(all_card_ids)).all()
        if all_card_ids else []
    )
    cards_dict = {c.card_id: _card_orm_to_domain(c) for c in cards_orm}

    from app.infrastructure.persistence.repositories.collection_repo import CollectionRepository
    collection_repo = CollectionRepository(db)

    missing_list: list[MissingCard] = []
    for dc in deck_cards_orm:
        owned = collection_repo.get_owned(dc.card_id)
        if owned < dc.qty:
            card = cards_dict.get(dc.card_id)
            missing_list.append(MissingCard(
                card_id=dc.card_id,
                name=card.name if card else dc.card_id,
                needed=dc.qty,
                owned=owned,
                missing=dc.qty - owned,
            ))

    from app.application.services.price_service import PriceService
    try:
        price_service = PriceService(db)
        price_service.ensure_fresh()
        prices = price_service.get_prices([mc.card_id for mc in missing_list])
    except Exception:
        prices = {}
    total_missing_price = 0.0
    has_any_price = False
    for mc in missing_list:
        p = prices.get(mc.card_id)
        if p:
            price = p.get("avg_price")
            if price is None:
                price = p.get("trend_price")
            if price is not None:
                mc.avg_price = price
                mc.extended_price = round(price * mc.missing, 2)
                total_missing_price += mc.extended_price
                has_any_price = True

    collection_all = collection_repo.export_collection()
    deck_card_ids = {dc.card_id for dc in deck_cards_orm}
    candidate_ids = [
        cid for cid, owned in collection_all.items()
        if cid not in deck_card_ids and owned > 0
    ]
    candidate_orms = (
        db.query(CardORM).filter(CardORM.card_id.in_(candidate_ids)).all()
        if candidate_ids else []
    )
    candidate_cards = {c.card_id: _card_orm_to_domain(c) for c in candidate_orms}

    leader_orm = db.query(CardORM).filter(CardORM.card_id == deck_orm.leader_card_id).first()
    leader_card = _card_orm_to_domain(leader_orm) if leader_orm else None

    from app.domain.engines.deck.substitution_scorer import SubstitutionScorer
    scorer = SubstitutionScorer()

    domain_deck = Deck(
        deck_id=deck_orm.deck_id,
        name=deck_orm.name,
        leader_card_id=deck_orm.leader_card_id,
        source=deck_orm.source,
        event=deck_orm.event,
        date=deck_orm.date,
        cards=[(dc.card_id, dc.qty) for dc in deck_cards_orm],
    )

    substitutions: list[SubstitutionSuggestion] = []
    for mc in missing_list:
        card_out = cards_dict.get(mc.card_id)
        if not card_out or not leader_card:
            continue
        best_score = 0
        best_candidate = None
        for cand_id, cand_card in candidate_cards.items():
            s = scorer.score(card_out, cand_card, domain_deck, leader_card)
            if s > best_score:
                best_score = s
                best_candidate = cand_card
        if best_candidate:
            substitutions.append(SubstitutionSuggestion(
                card_out_id=mc.card_id,
                card_in_id=best_candidate.card_id,
                card_in_name=best_candidate.name,
                score=best_score,
                image_url=best_candidate.image_url or None,
            ))

    fmt_name = format_name
    if not fmt_name:
        settings_repo = SettingsRepository(db)
        fmt_name = settings_repo.get("active_format")
    format_bans = None
    if fmt_name:
        fmt_repo = FormatRepository(db)
        fmt = fmt_repo.get_by_name(fmt_name)
        if fmt:
            format_bans = {
                "banned_cards": fmt.banned_cards or [],
                "banned_sets": fmt.banned_sets or [],
                "banned_blocks": fmt.banned_blocks or [],
                "banned_pair1": fmt.banned_pair1 or [],
                "banned_pair2": fmt.banned_pair2 or [],
            }

    validator = RuleValidator()
    result = validator.validate(domain_deck, cards_dict, format_bans)

    return CompleteDeckResponse(
        missing=missing_list,
        substitutions=substitutions,
        validation=ValidationResultResponse(
            errors=result.errors,
            warnings=result.warnings,
        ),
        total_missing_price=round(total_missing_price, 2) if has_any_price else None,
    )
