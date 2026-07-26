from fastapi import APIRouter
from backend.config import get_settings
from backend.models.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    provider = "live_granite" if settings.has_watsonx_credentials else "cached_demo"
    return HealthResponse(status="ok", provider=provider, version="0.1.0")
