"""Районы: список (для фильтра) и справка по району (TASK-104)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from bina.application.cities import city as city_info
from bina.application.cities import city_name
from bina.application.district_guide import (
    TAG_LABELS,
    distance_km,
    guide_for,
    minutes_to_center,
)
from bina.infrastructure.api.delivery import ui_language
from bina.infrastructure.api.dependencies import CurrentUserDep, SessionDep
from bina.infrastructure.api.routes.common import not_found
from bina.infrastructure.api.schemas import (
    CityCode,
    DistrictOut,
    DistrictsOut,
    Localized,
    localized,
)
from bina.infrastructure.db.repositories.districts import DistrictsRepository
from bina.infrastructure.db.repositories.listings import ListingsRepository

router = APIRouter(prefix="/api/districts", tags=["districts"])

NOTE = {
    "ka": "ფასები — ამჟამად ძებნაში არსებული განცხადებების მედიანა. დრო ცენტრამდე — "
    "მიახლოებით, მანქანით.",
    "ru": "Цены — медиана по объявлениям, которые сейчас в поиске. Время до центра — "
    "примерно, на машине.",
    "en": "Prices are the median of listings currently in search. Time to the centre is "
    "approximate, by car.",
}


class TagOut(BaseModel):
    code: str
    title: str


class MedianRentOut(BaseModel):
    rooms: int = Field(description="Комнат; 4 — «4 и больше»")
    price: int


class DistrictInfoOut(BaseModel):
    """Справка по району; тексты — на языке пользователя, цены — в лари."""

    id: UUID
    name: str
    names: Localized
    city: str = Field(default="tbilisi", description="Код города")
    city_name: str = ""
    latitude: float | None = None
    longitude: float | None = None
    distance_km: float | None = Field(
        default=None,
        description="По прямой до центра: Тбилиси — площадь Свободы, Батуми — площадь Европы",
    )
    minutes_to_center: int | None = None
    metro: bool | None = None
    tags: list[TagOut]
    about: str | None = None
    listings: int
    currency: str = "GEL"
    median_rent: list[MedianRentOut]
    median_per_m2: float | None = None
    note: str


@router.get("", response_model=DistrictsOut)
async def list_districts(
    session: SessionDep,
    city: Annotated[
        CityCode | None, Query(description="Только районы города; пусто — все (TASK-079)")
    ] = None,
) -> DistrictsOut:
    """Районы (для фильтра и названий в карточках)."""
    districts = await DistrictsRepository(session).list_all(city)
    return DistrictsOut(items=[DistrictOut.from_model(district) for district in districts])


@router.get("/{district_id}", response_model=DistrictInfoOut)
async def district_info(
    district_id: str, user: CurrentUserDep, session: SessionDep
) -> DistrictInfoOut:
    """Где район, есть ли метро, какой он, сколько объявлений и обычные цены."""
    try:
        uuid = UUID(district_id)
    except ValueError as exc:
        raise not_found("District not found") from exc
    district = await DistrictsRepository(session).get_by_id(uuid)
    if district is None or district.is_deleted:
        raise not_found("District not found")
    language = ui_language(user)
    names = {"ka": district.name_ka, "ru": district.name_ru, "en": district.name_en}
    stats = await ListingsRepository(session).district_stats(district.id)
    guide = guide_for(district.name_en, district.city)
    info = DistrictInfoOut(
        id=district.id,
        name=names[language],
        names=localized(**names),
        city=district.city,
        city_name=city_name(district.city, language),
        tags=[],
        listings=stats.listings,
        median_rent=[
            MedianRentOut(rooms=rooms, price=int(price))
            for rooms, price in sorted(stats.median_rent.items())
        ],
        median_per_m2=float(stats.median_per_m2) if stats.median_per_m2 is not None else None,
        note=NOTE[language],
    )
    if guide is None:
        return info
    return info.model_copy(
        update={
            "latitude": guide.latitude,
            "longitude": guide.longitude,
            "distance_km": round(
                distance_km(guide.latitude, guide.longitude, *city_info(district.city).center), 1
            ),
            "minutes_to_center": minutes_to_center(guide.latitude, guide.longitude, district.city),
            "metro": guide.metro,
            "tags": [TagOut(code=tag.value, title=TAG_LABELS[tag][language]) for tag in guide.tags],
            "about": guide.about[language] if guide.about else None,
        }
    )
