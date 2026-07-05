import json
from pathlib import Path

TRANSLATIONS_DIR = Path(__file__).resolve().parents[2] / "app" / "core" / "locales"

_translations: dict[str, dict] = {}

def load_translations(lang: str) -> dict:
    if lang not in _translations:
        filepath = TRANSLATIONS_DIR / f"{lang}.json"
        if filepath.exists():
            _translations[lang] = json.loads(filepath.read_text(encoding="utf-8"))
        else:
            _translations[lang] = {}
    return _translations[lang]

def t(key: str, lang: str = "es", **kwargs) -> str:
    translations = load_translations(lang)
    value = translations.get(key, key)
    if kwargs:
        try:
            value = value.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return value
