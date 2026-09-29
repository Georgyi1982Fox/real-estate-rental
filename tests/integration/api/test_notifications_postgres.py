"""Сохранённые поиски и уведомления на настоящем PostgreSQL (TASK-028).

Сценарий: пользователь сохраняет поиск через API → парсер находит подходящую и
неподходящую квартиры → создаются уведомления (повторный запуск дублей не даёт)
→ квартира из избранного дешевеет → уведомление «цена снижена» → отправка в
Telegram (фейковый отправитель) → список, счётчик, прочтение через API.
"""

import dataclasses
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.notification_sender import DeliveryResult, INotificationSender
from bina.application.ports.scraper import RawListing
from bina.application.repositories.notifications import PendingNotification
from bina.application.use_cases.notifications import (
    CreateNotificationsUseCase,
    DeliverNotificationsUseCase,
)
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import District, User
from bina.infrastructure.db.models.users import SubscriptionTier
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.db.repositories.notifications import (
    NotificationsRepository,
    SavedSearchesRepository,
)
from tests.support.telegram import sign_init_data

BOT_TOKEN = "123456:TEST-TOKEN"
USER = {"id": 777, "first_name": "Nino", "language_code": "ru"}
OTHER = {"id": 888, "first_name": "Giorgi", "language_code": "en"}


def headers(user: dict[str, object]) -> dict[str, str]:
    return {"X-Telegram-Init-Data": sign_init_data(BOT_TOKEN, user)}


def raw(source_id: str, price: float, rooms: int = 2, district: str = "Ваке") -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name="ss",
        title=f"Квартира {source_id}",
        description="",
        price=price,
        currency="GEL",
        rooms=rooms,
        area=60.0,
        district=district,
        url=f"https://home.ss.ge/ru/{source_id}",
        photos=[f"https://static.ss.ge/{source_id}.jpg"],
    )


class RecordingSender(INotificationSender):
    def __init__(self) -> None:
        self.sent: list[PendingNotification] = []

    async def send(self, pending: PendingNotification) -> DeliveryResult:
        self.sent.append(pending)
        return DeliveryResult.SENT


@pytest.fixture
async def client(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncClient]:
    app = create_app(ApiSettings(bot_token=BOT_TOKEN), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


@pytest.fixture
async def vake(session: AsyncSession) -> District:
    district = District(
        name_ru="Ваке",
        name_ka="ვაკე",
        name_en="Vake",
        avg_price_per_m2=Decimal(20),
        safety_score=9,
    )
    session.add(district)
    await session.commit()
    return district


async def create_notifications(session: AsyncSession) -> tuple[int, int]:
    result = await CreateNotificationsUseCase(
        SavedSearchesRepository(session),
        ListingsRepository(session),
        NotificationsRepository(session),
    ).execute()
    await session.commit()
    return result.new_listings, result.price_drops


async def test_saved_search_crud(client: AsyncClient, vake: District) -> None:
    assert (await client.get("/api/searches")).status_code == 401

    response = await client.post(
        "/api/searches",
        json={"filters": {"district": str(vake.id), "rooms": 2, "max_price": 2000}},
        headers=headers(USER),
    )
    assert response.status_code == 201, response.text
    search = response.json()
    assert search["name"] == "Ваке, 2 комн., до 2 000 ₾"
    assert search["filters"] == {
        "district": str(vake.id),
        "districts": [str(vake.id)],
        "min_price": None,
        "max_price": 2000.0,
        "rooms": 2,
        # TASK-086: остальные фильтры не заданы
        "min_area": None,
        "max_area": None,
        "q": None,
        "floor_min": None,
        "floor_max": None,
        "not_first_floor": False,
        "not_last_floor": False,
        "bedrooms": None,
        "bathrooms": None,
        "features": [],
        "condition": [],
        "owner_only": False,
    }
    assert (search["notify"], search["new_count"]) == (True, 0)

    bad = await client.post(
        "/api/searches",
        json={"filters": {"min_price": 3000, "max_price": 1000}},
        headers=headers(USER),
    )
    assert bad.status_code == 422

    patched = await client.patch(
        f"/api/searches/{search['id']}",
        json={"name": "Моя Ваке", "notify": False},
        headers=headers(USER),
    )
    assert (patched.json()["name"], patched.json()["notify"]) == ("Моя Ваке", False)

    # Чужой поиск не виден и не меняется
    other = await client.patch(
        f"/api/searches/{search['id']}", json={"notify": True}, headers=headers(OTHER)
    )
    assert other.status_code == 404
    assert (await client.get("/api/searches", headers=headers(OTHER))).json() == {"items": []}

    delete = await client.delete(f"/api/searches/{search['id']}", headers=headers(USER))
    assert delete.status_code == 204
    assert (await client.get("/api/searches", headers=headers(USER))).json() == {"items": []}


async def make_premium(session: AsyncSession, telegram_id: int = 777) -> None:
    await session.execute(
        update(User)
        .where(User.telegram_id == telegram_id)
        .values(
            subscription_tier=SubscriptionTier.NOMAD,
            subscription_expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    await session.commit()


async def test_free_plan_alerts_are_delayed(
    client: AsyncClient, session: AsyncSession, vake: District
) -> None:
    """TASK-085: бесплатному тарифу новая квартира приходит через 3 часа, Premium — сразу."""
    await client.post(
        "/api/searches", json={"filters": {"district": str(vake.id)}}, headers=headers(USER)
    )
    await ListingsRepository(session).create_or_update_from_raw(raw("1", 1500))
    await session.commit()
    assert await create_notifications(session) == (1, 0)

    sender = RecordingSender()
    now = datetime.now(UTC)
    deliver = DeliverNotificationsUseCase(NotificationsRepository(session), sender)
    assert (await deliver.execute(now=now)).sent == 0, "бесплатно: ещё рано"
    assert (await deliver.execute(now=now + timedelta(hours=3, minutes=1))).sent == 1
    await session.commit()

    # С Premium — сразу
    await make_premium(session)
    await ListingsRepository(session).create_or_update_from_raw(raw("2", 1600))
    await session.commit()
    assert await create_notifications(session) == (1, 0)
    assert (await deliver.execute(now=datetime.now(UTC))).sent == 1


async def test_notifications_flow(
    client: AsyncClient, session: AsyncSession, vake: District
) -> None:
    response = await client.post(
        "/api/searches",
        json={"filters": {"district": str(vake.id), "rooms": 2, "max_price": 2000}},
        headers=headers(USER),
    )
    search_id = response.json()["id"]

    # Парсер: подходящая, дорогая и в другом районе
    repository = ListingsRepository(session)
    match = await repository.create_or_update_from_raw(raw("1", 1500))
    await repository.create_or_update_from_raw(raw("2", 3500))
    await repository.create_or_update_from_raw(raw("3", 1500, district="Глдани"))
    await session.commit()

    assert await create_notifications(session) == (1, 0)
    assert await create_notifications(session) == (0, 0), "повторный запуск без дублей"

    searches = (await client.get("/api/searches", headers=headers(USER))).json()["items"]
    assert searches[0]["new_count"] == 1
    viewed = await client.post(f"/api/searches/{search_id}/viewed", headers=headers(USER))
    assert viewed.status_code == 204
    searches = (await client.get("/api/searches", headers=headers(USER))).json()["items"]
    assert searches[0]["new_count"] == 0

    # Избранная квартира подешевела
    favorite = await client.post(
        "/api/favorites", json={"listing_id": str(match.id)}, headers=headers(USER)
    )
    assert favorite.status_code == 201
    await repository.create_or_update_from_raw(raw("1", 1200))
    await session.commit()
    assert await create_notifications(session) == (0, 0), "«цена снижена» — только Premium"
    await make_premium(session)
    assert await create_notifications(session) == (0, 1)
    assert await create_notifications(session) == (0, 0)

    # Отправка в Telegram
    sender = RecordingSender()
    delivery = await DeliverNotificationsUseCase(NotificationsRepository(session), sender).execute()
    await session.commit()
    assert (delivery.sent, delivery.skipped, delivery.failed) == (2, 0, 0)
    assert {item.notification.type for item in sender.sent} == {"new_listing", "price_drop"}
    assert {item.telegram_id for item in sender.sent} == {777}
    new_listing = next(item for item in sender.sent if item.notification.type == "new_listing")
    assert new_listing.search_name == "Ваке, 2 комн., до 2 000 ₾"
    again = await DeliverNotificationsUseCase(NotificationsRepository(session), sender).execute()
    assert again.sent == 0, "отправленные не отправляются повторно"

    # API уведомлений
    count = (await client.get("/api/notifications/unread-count", headers=headers(USER))).json()
    assert count == {"count": 2}
    body = (await client.get("/api/notifications", headers=headers(USER))).json()
    assert (body["total"], body["unread_count"], body["page"], body["pages"]) == (2, 2, 1, 1)
    drop = next(item for item in body["items"] if item["type"] == "price_drop")
    assert drop["old_price"] == 1500.0
    assert drop["listing"]["price"] == 1200.0
    assert drop["listing"]["image"] == "https://static.ss.ge/1.jpg"
    assert drop["listing"]["title"] == {"ru": "Квартира 1"}
    new = next(item for item in body["items"] if item["type"] == "new_listing")
    assert (new["search_id"], new["search_name"]) == (search_id, "Ваке, 2 комн., до 2 000 ₾")

    # Чужое уведомление прочитать нельзя
    other = await client.post(f"/api/notifications/{new['id']}/read", headers=headers(OTHER))
    assert other.status_code == 404
    read = await client.post(f"/api/notifications/{new['id']}/read", headers=headers(USER))
    assert read.status_code == 204
    unread = (
        await client.get("/api/notifications", params={"filter": "unread"}, headers=headers(USER))
    ).json()
    assert [item["type"] for item in unread["items"]] == ["price_drop"]

    assert (
        await client.post("/api/notifications/read-all", headers=headers(USER))
    ).status_code == 204
    count = (await client.get("/api/notifications/unread-count", headers=headers(USER))).json()
    assert count == {"count": 0}


async def test_notifications_off_and_back_on(
    client: AsyncClient, session: AsyncSession, vake: District
) -> None:
    response = await client.post(
        "/api/searches",
        json={"filters": {"district": str(vake.id)}, "notify": False},
        headers=headers(USER),
    )
    search_id = response.json()["id"]
    repository = ListingsRepository(session)
    await repository.create_or_update_from_raw(raw("10", 1000))
    await session.commit()
    assert await create_notifications(session) == (0, 0), "уведомления выключены"

    # Включили: о квартирах, появившихся пока было выключено, не уведомляем
    await client.patch(f"/api/searches/{search_id}", json={"notify": True}, headers=headers(USER))
    assert await create_notifications(session) == (0, 0)
    await repository.create_or_update_from_raw(raw("11", 1000))
    await session.commit()
    assert await create_notifications(session) == (1, 0)


async def test_search_with_several_districts(
    client: AsyncClient, session: AsyncSession, vake: District
) -> None:
    """Поиск по нескольким районам: API списка, сохранённый поиск и уведомления."""
    repository = ListingsRepository(session)
    in_vake = await repository.create_or_update_from_raw(raw("v1", 1500))
    in_saburtalo = await repository.create_or_update_from_raw(raw("s1", 1400, district="Сабуртало"))
    await repository.create_or_update_from_raw(raw("d1", 1300, district="Дидубе"))
    await session.commit()
    vake_id, saburtalo_id = in_vake.district_id, in_saburtalo.district_id
    both = {str(in_vake.id), str(in_saburtalo.id)}

    # Повтором параметра и через запятую — одно и то же
    for query in (
        f"district={vake_id}&district={saburtalo_id}",
        f"district={vake_id},{saburtalo_id}",
    ):
        body = (await client.get(f"/api/listings?{query}")).json()
        assert {item["id"] for item in body["items"]} == both
    assert (await client.get("/api/listings?district=nope")).status_code == 422

    response = await client.post(
        "/api/searches",
        json={"filters": {"districts": [str(vake_id), str(saburtalo_id)]}},
        headers=headers(OTHER),
    )
    assert response.status_code == 201, response.text
    search = response.json()
    # Район из парсера сразу получает название на английском (TASK-019)
    assert search["name"] == "Vake, Saburtalo"
    assert search["filters"]["district"] is None
    assert search["filters"]["districts"] == [str(vake_id), str(saburtalo_id)]

    # Новые квартиры в обоих районах попадают в уведомления, в третьем — нет
    await repository.create_or_update_from_raw(raw("v2", 1600))
    await repository.create_or_update_from_raw(raw("s2", 1700, district="Сабуртало"))
    await repository.create_or_update_from_raw(raw("d2", 1800, district="Дидубе"))
    await session.commit()
    new_listings, _ = await create_notifications(session)
    assert new_listings == 2


async def test_saved_search_keeps_all_filters(
    client: AsyncClient, session: AsyncSession, vake: District
) -> None:
    """TASK-086: этаж, удобства, состояние, собственник, площадь сохраняются и работают."""
    filters = {
        "district": str(vake.id),
        "min_area": 50,
        "floor_min": 2,
        "not_last_floor": True,
        "bedrooms": 2,
        "features": ["air_conditioning", "furniture"],
        "condition": ["newly_renovated"],
        "owner_only": True,
    }
    response = await client.post("/api/searches", json={"filters": filters}, headers=headers(USER))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Ваке, ещё фильтров: 7"
    saved = body["filters"]
    assert (saved["min_area"], saved["floor_min"], saved["bedrooms"]) == (50, 2, 2)
    assert saved["features"] == ["furniture", "air_conditioning"]
    assert saved["condition"] == ["newly_renovated"]
    assert (saved["not_last_floor"], saved["owner_only"], saved["not_first_floor"]) == (
        True,
        True,
        False,
    )

    def detailed(source_id: str, **fields: object) -> RawListing:
        values: dict[str, object] = {
            "has_details": True,
            "floor": 3,
            "total_floors": 9,
            "bedrooms": 2,
            "features": ["furniture", "air_conditioning", "balcony"],
            "condition": "newly_renovated",
            "owner_type": "owner",
            **fields,
        }
        return dataclasses.replace(raw(source_id, 1500), **values)  # type: ignore[arg-type]

    repository = ListingsRepository(session)
    for listing in (
        detailed("fits"),
        detailed("agent", owner_type="agent"),
        detailed("top-floor", floor=9),
        detailed("no-ac", features=["furniture"]),
        detailed("old-repair", condition="needs_renovation"),
        detailed("small", area=40.0),
    ):
        await repository.create_or_update_from_raw(listing)
    await session.commit()

    assert await create_notifications(session) == (1, 0)
    searches = (await client.get("/api/searches", headers=headers(USER))).json()["items"]
    assert searches[0]["new_count"] == 1
    assert searches[0]["filters"]["features"] == ["furniture", "air_conditioning"]


@pytest.mark.parametrize(
    "filters",
    [{"features": ["jacuzzi"]}, {"condition": ["palace"]}, {"min_area": 80, "max_area": 50}],
)
async def test_saved_search_rejects_bad_filters(
    client: AsyncClient, filters: dict[str, object]
) -> None:
    response = await client.post("/api/searches", json={"filters": filters}, headers=headers(USER))
    assert response.status_code == 422
