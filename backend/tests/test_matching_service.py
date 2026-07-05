from unittest.mock import MagicMock, patch

from app.application.services.matching_service import MatchingService
from app.domain.engines.deck.card_matcher import CardMatcher
from app.domain.models import Card


def make_card(**kwargs) -> Card:
    defaults = dict(
        card_id="TEST-001",
        name="Test",
        cost=None,
        power=None,
        counter=0,
        type="Character",
        color=["Red"],
        traits=["Straw Hat Crew"],
        attribute=None,
        keywords=[],
        roles=[],
        effect="",
        life=None,
        set_id="TEST",
        set_name="Test Set",
        rarity="C",
        image_url="",
        unlimited_copies=False,
    )
    defaults.update(kwargs)
    return Card(**defaults)


def _make_orm_mock(card: Card):
    orm = MagicMock()
    orm.card_id = card.card_id
    orm.name = card.name
    orm.cost = card.cost
    orm.power = card.power
    orm.counter = card.counter
    orm.type = card.type
    orm.color = card.color
    orm.traits = card.traits
    orm.attribute = card.attribute
    orm.keywords = card.keywords
    orm.roles = card.roles
    orm.effect = card.effect
    orm.life = card.life
    orm.set_id = card.set_id
    orm.set_name = card.set_name
    orm.rarity = card.rarity
    orm.image_url = card.image_url
    orm.unlimited_copies = card.unlimited_copies
    return orm


def test_find_similar():
    query_card = make_card(
        card_id="Q1", type="Character", cost=3, power=5000, roles=["2k_counter"], effect="Block"
    )
    cand_card = make_card(
        card_id="C1", type="Character", cost=3, power=5000, roles=["2k_counter"], effect="Block"
    )

    mock_emb_service = MagicMock()
    mock_emb_service.embed.return_value = [1.0, 0.0, 0.0]

    mock_card_index = MagicMock()
    mock_card_index.get_embedding.return_value = None
    mock_card_index.query.return_value = [("C1", 0.95)]
    mock_card_index.get_embedding.return_value = None

    mock_session = MagicMock()
    mock_repo = MagicMock()
    mock_repo.get_by_id.side_effect = lambda cid: _make_orm_mock(
        query_card if cid == "Q1" else cand_card
    )

    with (
        patch(
            "app.application.services.matching_service.SessionLocal",
            return_value=mock_session,
        ),
        patch(
            "app.application.services.matching_service.CardRepository",
            return_value=mock_repo,
        ),
    ):
        service = MatchingService(
            embedding_service=mock_emb_service,
            card_index=mock_card_index,
            matcher=CardMatcher(),
        )
        results = service.find_similar("Q1", top_k=10)

    assert len(results) == 1
    assert results[0]["card_id"] == "C1"
    assert results[0]["score"] > 0.0
    assert mock_emb_service.embed.call_count == 2


def test_find_similar_card_not_found():
    mock_emb_service = MagicMock()
    mock_card_index = MagicMock()
    mock_session = MagicMock()
    mock_repo = MagicMock()
    mock_repo.get_by_id.return_value = None

    with (
        patch(
            "app.application.services.matching_service.SessionLocal",
            return_value=mock_session,
        ),
        patch(
            "app.application.services.matching_service.CardRepository",
            return_value=mock_repo,
        ),
    ):
        service = MatchingService(
            embedding_service=mock_emb_service,
            card_index=mock_card_index,
            matcher=CardMatcher(),
        )
        results = service.find_similar("NONEXIST", top_k=10)

    assert results == []


def test_find_similar_uses_cached_embedding():
    query_card = make_card(
        card_id="Q1", type="Character", cost=3, power=5000, effect="Block"
    )
    cand_card = make_card(
        card_id="C1", type="Character", cost=3, power=5000, effect="Block"
    )

    mock_emb_service = MagicMock()
    mock_card_index = MagicMock()
    mock_card_index.get_embedding.side_effect = [
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
    ]
    mock_card_index.query.return_value = [("C1", 0.95)]

    mock_session = MagicMock()
    mock_repo = MagicMock()
    mock_repo.get_by_id.side_effect = lambda cid: _make_orm_mock(
        query_card if cid == "Q1" else cand_card
    )

    with (
        patch(
            "app.application.services.matching_service.SessionLocal",
            return_value=mock_session,
        ),
        patch(
            "app.application.services.matching_service.CardRepository",
            return_value=mock_repo,
        ),
    ):
        service = MatchingService(
            embedding_service=mock_emb_service,
            card_index=mock_card_index,
            matcher=CardMatcher(),
        )
        results = service.find_similar("Q1", top_k=10)

    mock_emb_service.embed.assert_not_called()
    assert len(results) == 1
