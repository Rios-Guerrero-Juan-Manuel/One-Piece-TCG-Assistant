from app.infrastructure.importers.keyword_extractor import KeywordExtractor


def test_extract_blocker():
    result = KeywordExtractor.extract("This card has [Blocker].")
    assert "blocker" in result

def test_extract_rush():
    result = KeywordExtractor.extract("Give [Rush] to one character.")
    assert "rush" in result

def test_extract_multiple():
    result = KeywordExtractor.extract("[Blocker] [Rush] [Banish]")
    assert "blocker" in result
    assert "rush" in result
    assert "banish" in result

def test_extract_empty():
    result = KeywordExtractor.extract("A vanilla card with no keywords.")
    assert result == []

def test_extract_trigger():
    result = KeywordExtractor.extract("[Trigger] Draw 1 card.")
    assert "trigger" in result
