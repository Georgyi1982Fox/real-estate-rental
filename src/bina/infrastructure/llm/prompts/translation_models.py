from pydantic import BaseModel


class TranslationResponse(BaseModel):
    """Модель ответа для перевода объявления."""
    title_ru: str
    description_ru: str