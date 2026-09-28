from uuid import UUID

from pydantic import BaseModel


class TranslatedListingDTO(BaseModel):
    """DTO для переведенного объявления."""

    id: UUID
    title_ru: str
    description_ru: str
    price: float
    rooms: int
    area: float
