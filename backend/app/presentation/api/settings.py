from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application.event_bus import get_event_bus
from app.core.config import settings as app_settings
from app.domain.events import SettingsChanged
from app.infrastructure.persistence.repositories.settings_repo import SettingsRepository
from app.infrastructure.persistence.session import get_db
from app.presentation.schemas.settings_schema import SettingsResponse, SettingsUpdateRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    repo = SettingsRepository(db)
    result = repo.get_all()
    result.setdefault("self_user", app_settings.self_user)
    result.setdefault("language", app_settings.language)
    return SettingsResponse(settings=result)


@router.put("", response_model=SettingsResponse)
async def update_settings(req: SettingsUpdateRequest, db: Session = Depends(get_db)):
    repo = SettingsRepository(db)
    for key, value in req.settings.items():
        repo.set(key, value)
        get_event_bus().publish(
            "SettingsChanged",
            SettingsChanged(key=key, value=value),
        )
    db.commit()
    result = repo.get_all()
    result.setdefault("self_user", app_settings.self_user)
    result.setdefault("language", app_settings.language)
    return SettingsResponse(settings=result)
