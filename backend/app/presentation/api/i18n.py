import json
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/i18n", tags=["i18n"])

LOCALES_DIR = Path(__file__).resolve().parents[3] / "app" / "core" / "locales"


@router.get("/{lang}")
async def get_translations(lang: str):
    filepath = LOCALES_DIR / f"{lang}.json"
    if filepath.exists():
        translations = json.loads(filepath.read_text(encoding="utf-8"))
    else:
        filepath = LOCALES_DIR / "es.json"
        translations = json.loads(filepath.read_text(encoding="utf-8"))
    return {"lang": lang, "translations": translations}
