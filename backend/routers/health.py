from fastapi import APIRouter
from backend.config import get_settings
from backend.models.schemas import HealthResponse

router = APIRouter()


def _get_actual_provider(settings) -> str:
    """Return the provider that would actually be used for Granite calls."""
    if not settings.has_watsonx_credentials:
        return "cached_demo"
    try:
        from ibm_watsonx_ai.foundation_models import ModelInference  # noqa: F401
        return "live_granite"
    except Exception:
        return "cached_demo"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    provider = _get_actual_provider(settings)
    return HealthResponse(status="ok", provider=provider, version="0.1.0")
