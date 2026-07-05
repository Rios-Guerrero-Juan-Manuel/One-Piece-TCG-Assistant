from app.domain.engines.deck.role_classifier import RoleClassifier
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


def test_2k_blocker_gets_roles():
    card = make_card(
        cost=2,
        counter=2000,
        keywords=["blocker"],
        effect="[Blocker]",
    )
    roles = RoleClassifier.classify(card)
    assert "2k_counter" in roles
    assert "early_blocker" in roles


def test_searcher_gets_engine_and_searcher():
    card = make_card(
        cost=3,
        counter=0,
        keywords=["search"],
        effect="Search your deck for 1 card.",
    )
    roles = RoleClassifier.classify(card)
    assert "engine" in roles
    assert "searcher" in roles


def test_boss_character():
    card = make_card(
        cost=8,
        power=9000,
        counter=0,
        type="Character",
        effect="A powerful boss character.",
    )
    roles = RoleClassifier.classify(card)
    assert "boss" in roles
