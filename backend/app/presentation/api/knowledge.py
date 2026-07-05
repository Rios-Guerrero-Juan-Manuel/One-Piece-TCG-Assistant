from fastapi import APIRouter

from app.application.services.knowledge_service import KnowledgeService
from app.infrastructure.persistence.session import SessionLocal

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _service() -> KnowledgeService:
    return KnowledgeService(SessionLocal)


@router.get("/insights")
async def get_insights():
    return _service().get_insights()


@router.post("/insights/generate")
async def generate_insights():
    return _service().generate_insights()
