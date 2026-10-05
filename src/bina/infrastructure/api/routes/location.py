"""Где квартира на карте (TASK-080): ``GET /api/listings/{id}/location``.

- ``exact`` — координаты из объявления (SS.ge, MyHome.ge) или найденные по адресу;
- ``district`` — точного места нет, показываем центр района («примерно»);
- ``none`` — неизвестно ни то, ни другое.

Ссылки открывают точку в Google Maps, Яндекс Картах и OpenStreetMap.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from bina.application.district_guide import guide_for
from bina.infrastructure.api.delivery import viewer_language
from bina.infrastructure.api.dependencies import OptionalUserDep, SessionDep
from bina.infrastructure.api.routes.common import get_listing_or_404

router = APIRouter(prefix="/api/listings", tags=["listings"])


class MapLinksOut(BaseModel):
    google: str
    yandex: str
    osm: str


class LocationOut(BaseModel):
    precision: Literal["exact", "district", "none"]
    latitude: float | None = None
    longitude: float | None = None
    district: str | None = None
    address: str | None = None
    links: MapLinksOut | None = None


def map_links(latitude: float, longitude: float, exact: bool) -> MapLinksOut:
    """Ссылки на точку; для центра района — карта помельче, без метки."""
    point = f"{latitude:.6f},{longitude:.6f}"
    zoom = 17 if exact else 14
    return MapLinksOut(
        google=f"https://www.google.com/maps/search/?api=1&query={point}",
        yandex=(
            f"https://yandex.com/maps/?ll={longitude:.6f},{latitude:.6f}&z={zoom}"
            + (f"&pt={longitude:.6f},{latitude:.6f}" if exact else "")
        ),
        osm=(
            f"https://www.openstreetmap.org/?mlat={latitude:.6f}&mlon={longitude:.6f}"
            f"#map={zoom}/{latitude:.6f}/{longitude:.6f}"
        ),
    )


@router.get("/{listing_id}/location", response_model=LocationOut)
async def listing_location(
    listing_id: str,
    user: OptionalUserDep,
    session: SessionDep,
    lang: Annotated[str | None, Query(pattern="^(ka|ru|en)$")] = None,
) -> LocationOut:
    """Точка для карты в карточке объявления (и гостю сайта: язык — ``lang``)."""
    listing = await get_listing_or_404(session, listing_id)
    await session.refresh(listing, attribute_names=["district"])
    district = listing.district
    district_name = (
        {"ka": district.name_ka, "ru": district.name_ru, "en": district.name_en}[
            viewer_language(user, lang)
        ]
        if district
        else None
    )
    if listing.latitude is not None and listing.longitude is not None:
        return LocationOut(
            precision="exact",
            latitude=listing.latitude,
            longitude=listing.longitude,
            district=district_name,
            address=listing.address,
            links=map_links(listing.latitude, listing.longitude, exact=True),
        )
    guide = guide_for(district.name_en, district.city) if district else None
    if guide is None:
        return LocationOut(precision="none", district=district_name, address=listing.address)
    return LocationOut(
        precision="district",
        latitude=guide.latitude,
        longitude=guide.longitude,
        district=district_name,
        address=listing.address,
        links=map_links(guide.latitude, guide.longitude, exact=False),
    )
