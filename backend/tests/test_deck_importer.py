from app.infrastructure.importers.deck_importer import DeckImporter


def test_parse_deck_text():
    text = "1xOP16-079\n4xOP16-091\n4xOP16-092\n"
    leader, cards = DeckImporter.parse_deck_text(text)
    assert leader == "OP16-079"
    assert ("OP16-091", 4) in cards
    assert ("OP16-092", 4) in cards

def test_parse_deck_text_empty_lines():
    text = "\n1xOP16-079\n\n4xOP16-091\n\n"
    leader, cards = DeckImporter.parse_deck_text(text)
    assert leader == "OP16-079"
    assert len(cards) == 1
