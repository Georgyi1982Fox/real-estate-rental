from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class TranslatedListingDTO(BaseModel):
    """DTO для переведенного объявления."""
    id: UUID
    title_ru: str
    description_ru: str
    price: float
    rooms: int
    area: float