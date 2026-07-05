from __future__ import annotations

import csv
import io
import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories.card_repo import CardRepository
from app.infrastructure.persistence.repositories.collection_repo import (
    CollectionRepository,
)

logger = logging.getLogger(__name__)

_ONE_PIECE = "one piece"


@dataclass
class CsvImportReport:
    imported: int = 0
    total_owned: int = 0
    removed: int = 0
    skipped_other_tcg: int = 0
    skipped_japanese: int = 0
    skipped_no_card_number: int = 0
    synced: bool = False
    sync_failed: bool = False
    missing_card_ids: list[str] = field(default_factory=list)


def parse_collection_csv(csv_text: str) -> tuple[dict[str, int], CsvImportReport]:
    """Parse a collection export CSV into ``{card_id: owned}`` for English One Piece.

    Pure transformation with no DB access. Rules:

    * keep only ``Category == "One Piece"`` rows,
    * drop Japanese cards (``"(JP)"`` suffix in ``Product Name``),
    * drop rows without a ``Card Number`` (DON!! cards / tokens),
    * sum ``Quantity`` per card number (alternate arts share a number).
    """
    items: dict[str, int] = {}
    report = CsvImportReport()

    text = csv_text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        category = (row.get("Category") or "").strip()
        if category.lower() != _ONE_PIECE:
            report.skipped_other_tcg += 1
            continue

        product_name = row.get("Product Name") or ""
        if "(JP)" in product_name:
            report.skipped_japanese += 1
            continue

        card_number = (row.get("Card Number") or "").strip()
        if not card_number:
            report.skipped_no_card_number += 1
            continue

        quantity_raw = (row.get("Quantity") or "").strip()
        try:
            quantity = int(float(quantity_raw)) if quantity_raw else 0
        except (TypeError, ValueError):
            quantity = 0

        items[card_number] = items.get(card_number, 0) + quantity

    return items, report


def import_collection_csv(
    csv_text: str,
    session: Session,
    sync_missing_fn: Callable[[], object] | None = None,
) -> CsvImportReport:
    """Apply a collection CSV to the database as a full replace.

    The English One Piece subset of the CSV becomes the source of truth: cards
    present are set to their CSV quantity and cards absent are removed. Cards
    whose id is not yet in the DB cannot be stored (FK constraint); when
    ``sync_missing_fn`` is given it is invoked first to pull missing cards.
    """
    items, report = parse_collection_csv(csv_text)
    if not items:
        # Refuse to wipe the collection from an empty/invalid payload.
        return report

    card_repo = CardRepository(session)
    collection_repo = CollectionRepository(session)

    keep_ids = set(items.keys())
    existing = card_repo.existing_card_ids(keep_ids)
    missing = keep_ids - existing

    if missing and sync_missing_fn is not None:
        try:
            sync_missing_fn()
            report.synced = True
            # End the read transaction so the newly committed cards are visible.
            session.commit()
            existing = card_repo.existing_card_ids(keep_ids)
            missing = keep_ids - existing
        except Exception:
            report.sync_failed = True
            logger.warning("Card sync failed during CSV import", exc_info=True)

    existing_items = {card_id: items[card_id] for card_id in existing}
    collection_repo.import_collection(existing_items)
    report.removed = collection_repo.delete_where_card_id_not_in(keep_ids)

    report.imported = len(existing_items)
    report.total_owned = sum(existing_items.values())
    report.missing_card_ids = sorted(missing)
    return report
