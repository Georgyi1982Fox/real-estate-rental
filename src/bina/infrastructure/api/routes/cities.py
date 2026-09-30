"""Города для выбора в Mini App (TASK-079): ``GET /api/cities``."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from bina.application.cities import CITIES
from bina.infrastructure.api.schemas import Localized, localized

router = APIRouter(prefix="/api/cities", tags=["districts"])


class CityOut(BaseModel):
    code: str = Field(description="Параметр city в /api/listings и /api/districts")
    name: Localized
    latitude: float = Field(description="Центр города для карты")
    longitude: float


class CitiesOut(BaseModel):
    items: list[CityOut]


@router.get("", response_model=CitiesOut)
async def list_cities() -> CitiesOut:
    """Все города сервиса (без авторизации)."""
    return CitiesOut(
        items=[
            CityOut(
                code=city.code,
                name=localized(**city.names),
                latitude=city.center[0],
                longitude=city.center[1],
            )
            for city in CITIES.values()
        ]
    )
