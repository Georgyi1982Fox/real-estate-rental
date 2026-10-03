"""Города для выбора в Mini App (TASK-079): ``GET /api/cities``."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from bina.application.cities import city as city_info
from bina.infrastructure.api.dependencies import SessionDep
from bina.infrastructure.api.schemas import Localized, localized
from bina.infrastructure.db.repositories.districts import DistrictsRepository

router = APIRouter(prefix="/api/cities", tags=["districts"])


class CityOut(BaseModel):
    code: str = Field(description="Параметр city в /api/listings и /api/districts")
    name: Localized
    latitude: float = Field(description="Центр города для карты")
    longitude: float


class CitiesOut(BaseModel):
    items: list[CityOut]


@router.get("", response_model=CitiesOut)
async def list_cities(session: SessionDep) -> CitiesOut:
    """Города, в которых уже есть объявления (без авторизации).

    Пустые города не показываем: список растёт сам, когда парсер находит жильё в новом
    городе Грузии (TASK-079).
    """
    codes = await DistrictsRepository(session).cities()
    return CitiesOut(
        items=[
            CityOut(
                code=code,
                name=localized(**city_info(code).names),
                latitude=city_info(code).center[0],
                longitude=city_info(code).center[1],
            )
            for code in codes
        ]
    )
