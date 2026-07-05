from app.domain.engines.deck.substitution_scorer import SubstitutionScorer
from app.domain.models import Card, Deck


def _make_card(
    card_id="OP16-001",
    name="Test Card",
    cost=3,
    power=5000,
    counter=1000,
    type_="Character",
    color=None,
    traits=None,
    keywords=None,
    roles=None,
    effect="",
):
    return Card(
        card_id=card_id,
        name=name,
        cost=cost,
        power=power,
        counter=counter,
        type=type_,
        color=color or ["Red"],
        traits=traits or ["Straw Hat Crew"],
        attribute="Impact",
        keywords=keywords or ["blocker"],
        roles=roles or ["early_blocker", "2k_counter"],
        effect=effect,
        life=None,
        set_id="OP16",
        set_name="Test Set",
        rarity="Common",
        image_url="",
        unlimited_copies=False,
    )


def _make_deck(leader_id="OP16-079", cards=None):
    return Deck(
        deck_id="test-deck",
        name="Test Deck",
        leader_card_id=leader_id,
        source="test",
        event=None,
        date=None,
        cards=cards or [("OP16-001", 4), ("OP16-002", 4)],
    )


def test_identical_card_substitution_scores_high():
    card = _make_card()
    leader = _make_card(card_id="OP16-079", color=["Red"], traits=["Straw Hat Crew"])
    deck = _make_deck()
    scorer = SubstitutionScorer()
    result = scorer.score(card, card, deck, leader, embedding_sim=1.0)
    assert result >= 85


def test_completely_different_card_scores_low():
    card_out = _make_card(cost=3, color=["Red"], traits=["Straw Hat Crew"], roles=["early_blocker"])
    card_in = _make_card(
        card_id="OP16-099",
        cost=8,
        color=["Blue"],
        traits=["Navy"],
        roles=["boss"],
        keywords=["rush"],
    )
    leader = _make_card(card_id="OP16-079", color=["Red"], traits=["Straw Hat Crew"])
    deck = _make_deck()
    scorer = SubstitutionScorer()
    result = scorer.score(card_out, card_in, deck, leader, embedding_sim=0.0)
    assert result < 40


def test_same_cost_scores_higher_on_curve():
    card_same_cost = _make_card(card_id="OP16-002", cost=3)
    card_diff_cost = _make_card(card_id="OP16-003", cost=7)
    card_out = _make_card(cost=3)
    leader = _make_card(card_id="OP16-079")
    deck = _make_deck()
    scorer = SubstitutionScorer()
    score_same = scorer.score(card_out, card_same_cost, deck, leader, embedding_sim=0.5)
    score_diff = scorer.score(card_out, card_diff_cost, deck, leader, embedding_sim=0.5)
    assert score_same > score_diff


def test_color_match_with_leader_boosts_synergy():
    card_matching = _make_card(card_id="OP16-002", color=["Red"])
    card_nonmatching = _make_card(card_id="OP16-003", color=["Blue"])
    card_out = _make_card(color=["Red"])
    leader = _make_card(card_id="OP16-079", color=["Red"])
    deck = _make_deck()
    scorer = SubstitutionScorer()
    match_score = scorer.score(card_out, card_matching, deck, leader, embedding_sim=0.3)
    nonmatch_score = scorer.score(card_out, card_nonmatching, deck, leader, embedding_sim=0.3)
    assert match_score > nonmatch_score


def test_role_overlap_boosts_impact():
    card_same_roles = _make_card(
        card_id="OP16-002",
        roles=["early_blocker", "2k_counter"],
        keywords=["blocker"],
    )
    card_diff_roles = _make_card(
        card_id="OP16-003",
        roles=["boss", "finisher"],
        keywords=["rush"],
    )
    card_out = _make_card(roles=["early_blocker", "2k_counter"], keywords=["blocker"])
    leader = _make_card(card_id="OP16-079")
    deck = _make_deck()
    scorer = SubstitutionScorer()
    same_score = scorer.score(card_out, card_same_roles, deck, leader, embedding_sim=0.3)
    diff_score = scorer.score(card_out, card_diff_roles, deck, leader, embedding_sim=0.3)
    assert same_score > diff_score


def test_score_returns_int_0_to_100():
    card_out = _make_card()
    card_in = _make_card(card_id="OP16-099")
    leader = _make_card(card_id="OP16-079")
    deck = _make_deck()
    scorer = SubstitutionScorer()
    result = scorer.score(card_out, card_in, deck, leader, embedding_sim=0.5)
    assert isinstance(result, int)
    assert 0 <= result <= 100


def test_no_embedding_sim_falls_back_to_struct():
    card_out = _make_card()
    card_in_similar = _make_card(
        card_id="OP16-002",
        cost=3,
        power=5000,
        type_="Character",
        keywords=["blocker"],
        roles=["early_blocker", "2k_counter"],
    )
    card_in_different = _make_card(
        card_id="OP16-003",
        cost=8,
        power=9000,
        type_="Event",
        keywords=["rush"],
        roles=["boss"],
    )
    leader = _make_card(card_id="OP16-079")
    deck = _make_deck()
    scorer = SubstitutionScorer()
    sim_score = scorer.score(card_out, card_in_similar, deck, leader, embedding_sim=0.0)
    diff_score = scorer.score(card_out, card_in_different, deck, leader, embedding_sim=0.0)
    assert sim_score > diff_score
