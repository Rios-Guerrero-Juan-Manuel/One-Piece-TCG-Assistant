from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.application.services.collection_csv_import import import_collection_csv
from app.infrastructure.persistence.repositories.collection_repo import CollectionRepository
from app.infrastructure.persistence.session import get_db
from app.presentation.schemas.collection_schema import (
    CollectionImportRequest,
    CollectionItem,
    CollectionResponse,
    CollectionUpdateRequest,
    CsvImportResponse,
)

router = APIRouter(prefix="/api/collection", tags=["collection"])


def _sync_missing_cards() -> None:
    """Pull the full card catalogue from optcgapi (used when the CSV references
    card ids not yet in the DB)."""
    from app.infrastructure.importers.card_api_importer import CardApiImporter

    CardApiImporter().import_full()


@router.get("", response_model=CollectionResponse)
async def get_collection(db: Session = Depends(get_db)):
    repo = CollectionRepository(db)
    items = repo.get_all()
    return CollectionResponse(
        items=[CollectionItem(card_id=i.card_id, owned=i.owned) for i in items]
    )


@router.post("", response_model=CollectionItem)
async def update_owned(req: CollectionUpdateRequest, db: Session = Depends(get_db)):
    repo = CollectionRepository(db)
    item = repo.set_owned(req.card_id, req.owned)
    db.commit()
    return CollectionItem(card_id=item.card_id, owned=item.owned)


@router.post("/import")
async def import_collection(req: CollectionImportRequest, db: Session = Depends(get_db)):
    repo = CollectionRepository(db)
    count = repo.import_collection(req.items)
    db.commit()
    return {"imported": count}


@router.post("/import-csv", response_model=CsvImportResponse)
async def import_collection_csv_endpoint(
    file: UploadFile = File(...), db: Session = Depends(get_db)
):
    raw = await file.read()
    csv_text = raw.decode("utf-8-sig", errors="replace")
    report = import_collection_csv(csv_text, db, sync_missing_fn=_sync_missing_cards)
    db.commit()
    return CsvImportResponse(
        imported=report.imported,
        total_owned=report.total_owned,
        removed=report.removed,
        skipped_other_tcg=report.skipped_other_tcg,
        skipped_japanese=report.skipped_japanese,
        skipped_no_card_number=report.skipped_no_card_number,
        synced=report.synced,
        sync_failed=report.sync_failed,
        missing_card_ids=report.missing_card_ids,
    )


@router.get("/export")
async def export_collection(db: Session = Depends(get_db)):
    repo = CollectionRepository(db)
    return repo.export_collection()
