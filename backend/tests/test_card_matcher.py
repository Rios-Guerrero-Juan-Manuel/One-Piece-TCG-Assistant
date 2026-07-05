from app.domain.engines.deck.card_matcher import CardMatcher, _cosine_similarity, _jaccard
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


def test_cosine_similarity_identical():
    vec = [1.0, 0.0, 0.5]
    assert abs(_cosine_similarity(vec, vec) - 1.0) < 1e-9


def test_cosine_similarity_orthogonal():
    assert _cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_jaccard_full_overlap():
    assert _jaccard(["a", "b"], ["a", "b"]) == 1.0


def test_jaccard_no_overlap():
    assert _jaccard(["a"], ["b"]) == 0.0


def test_struct_similarity_same_type():
    matcher = CardMatcher()
    query = make_card(type="Character", cost=3, power=5000, keywords=["blocker"], traits=["X"])
    cand = make_card(
        card_id="CAND-1", type="Character", cost=3, power=5000, keywords=["blocker"], traits=["X"]
    )
    score = matcher._struct_similarity(query, cand)
    assert score >= 0.85


def test_struct_similarity_cost_close():
    matcher = CardMatcher()
    query = make_card(type="Character", cost=3, power=5000)
    close = make_card(card_id="C1", type="Character", cost=4, power=5000)
    far = make_card(card_id="C2", type="Character", cost=7, power=5000)
    score_close = matcher._struct_similarity(query, close)
    score_far = matcher._struct_similarity(query, far)
    assert score_close > score_far


def test_role_similarity():
    query = make_card(roles=["2k_counter", "blocker"])
    match = make_card(card_id="C1", roles=["2k_counter", "blocker"])
    no_match = make_card(card_id="C2", roles=["engine", "boss"])
    score_match = _jaccard(query.roles, match.roles)
    score_no_match = _jaccard(query.roles, no_match.roles)
    assert score_match > score_no_match
    assert score_match == 1.0
    assert score_no_match == 0.0


def test_composite_score_sorted():
    matcher = CardMatcher()
    query = make_card(
        type="Character", cost=3, power=5000, keywords=["blocker"], roles=["2k_counter"]
    )
    c1 = make_card(
        card_id="C1",
        type="Character",
        cost=3,
        power=5000,
        keywords=["blocker"],
        roles=["2k_counter"],
    )
    c2 = make_card(
        card_id="C2",
        type="Leader",
        cost=8,
        power=9000,
        keywords=["rush"],
        roles=["boss"],
    )
    query_emb = [1.0, 0.0, 0.0]
    embs = [[0.0, 1.0, 0.0], [1.0, 0.0, 0.0]]
    results = matcher.match(
        query_card=query,
        candidates=[c2, c1],
        query_embedding=query_emb,
        candidate_embeddings=embs,
        top_k=10,
    )
    assert len(results) == 2
    assert results[0][0].card_id == "C1"
    assert results[0][1] > results[1][1]


def test_top_k_limits_results():
    matcher = CardMatcher()
    query = make_card(type="Character", cost=3, power=5000)
    candidates = [
        make_card(card_id=f"C{i}", type="Character", cost=3, power=5000) for i in range(10)
    ]
    query_emb = [1.0, 0.0]
    embs = [[1.0, 0.0] for _ in range(10)]
    results = matcher.match(
        query_card=query,
        candidates=candidates,
        query_embedding=query_emb,
        candidate_embeddings=embs,
        top_k=3,
    )
    assert len(results) == 3


def test_empty_embeddings_returns_zero():
    matcher = CardMatcher()
    query = make_card(type="Character", cost=3, power=5000, traits=["X"], keywords=["a"])
    cand = make_card(
        card_id="C1", type="Leader", cost=8, power=9000, traits=["Y"], keywords=["b"]
    )
    results = matcher.match(
        query_card=query,
        candidates=[cand],
        query_embedding=[],
        candidate_embeddings=[[]],
        top_k=10,
    )
    assert len(results) == 1
    assert results[0][1] == 0.0
