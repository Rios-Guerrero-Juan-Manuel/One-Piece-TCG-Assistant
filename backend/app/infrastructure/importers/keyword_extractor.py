import re


class KeywordExtractor:
    PATTERNS = {
        "blocker": re.compile(r"\bblocker\b", re.IGNORECASE),
        "rush": re.compile(r"\brush\b", re.IGNORECASE),
        "banish": re.compile(r"\bbanish\b", re.IGNORECASE),
        "trigger": re.compile(r"\btrigger\b", re.IGNORECASE),
        "counter": re.compile(r"\bcounter\b", re.IGNORECASE),
        "draw": re.compile(r"draw\s+\d+\s+card", re.IGNORECASE),
        "search": re.compile(r"(?:search|look\s+at\s+\d+|reveal\s+\d+)", re.IGNORECASE),
        "reveal": re.compile(r"\breveal\b", re.IGNORECASE),
        "ko": re.compile(r"\b(?:ko|k\.o\.|knock\s+out)\b", re.IGNORECASE),
        "rest": re.compile(r"\brest\b", re.IGNORECASE),
        "trash": re.compile(r"\btrash\b", re.IGNORECASE),
        "ramp": re.compile(r"(?:don\s*\+\s*\d|extra\s+don|add\s+\d+\s+don)", re.IGNORECASE),
        "don_support": re.compile(r"for\s+each\s+(?:don|rested\s+don)", re.IGNORECASE),
        "heal": re.compile(r"\bheal\b", re.IGNORECASE),
        "guard_point": re.compile(r"guard\s+point", re.IGNORECASE),
    }

    @staticmethod
    def extract(card_text: str) -> list[str]:
        if not card_text:
            return []
        result: list[str] = []
        seen: set[str] = set()
        for keyword, pattern in KeywordExtractor.PATTERNS.items():
            if pattern.search(card_text):
                if keyword not in seen:
                    seen.add(keyword)
                    result.append(keyword)
        return result
