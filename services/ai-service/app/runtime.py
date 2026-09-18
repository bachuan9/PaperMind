from .models import ModelStatusResponse
from .settings import Settings


def get_model_status(settings: Settings) -> ModelStatusResponse:
    return ModelStatusResponse(
        provider="SiliconFlow",
        model=settings.llm_model,
        base_url=settings.deepseek_base_url,
        configured=bool(settings.deepseek_api_key),
    )
