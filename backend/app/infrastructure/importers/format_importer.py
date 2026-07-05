import json
import logging
from pathlib import Path

from app.infrastructure.persistence.repositories.format_repo import FormatRepository
from app.infrastructure.persistence.session import SessionLocal, init_db

logger = logging.getLogger(__name__)

FORMATS_DIR = Path(__file__).resolve().parents[4] / "Datos" / "1.40a" / "Formats"


class FormatImporter:
    def __init__(self, formats_dir: Path | None = None):
        self.formats_dir = formats_dir or FORMATS_DIR

    def import_all(self) -> dict:
        init_db()
        session = SessionLocal()
        results = {}
        try:
            repo = FormatRepository(session)
            for fmt_file in sorted(self.formats_dir.glob("*.json")):
                fmt_name = fmt_file.stem
                logger.info("Importing format: %s", fmt_name)
                data = json.loads(fmt_file.read_text(encoding="utf-8"))
                format_data = {
                    "format_name": fmt_name,
                    "banned_cards": data.get("bannedCards", []),
                    "banned_sets": data.get("bannedSets", []),
                    "banned_blocks": data.get("bannedBlocks", []),
                    "banned_pair1": data.get("bannedPair1", []),
                    "banned_pair2": data.get("bannedPair2", []),
                }
                repo.upsert(format_data)
                results[fmt_name] = len(data.get("bannedCards", []))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
        return results
