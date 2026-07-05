from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories.format_repo import FormatRepository
from app.infrastructure.persistence.session import get_db
from app.presentation.schemas.format_schema import FormatListResponse, FormatResponse

router = APIRouter(prefix="/api/formats", tags=["formats"])


@router.get("", response_model=FormatListResponse)
async def list_formats(db: Session = Depends(get_db)):
    repo = FormatRepository(db)
    formats = repo.get_all()
    return FormatListResponse(
        formats=[FormatResponse.model_validate(f) for f in formats]
    )
