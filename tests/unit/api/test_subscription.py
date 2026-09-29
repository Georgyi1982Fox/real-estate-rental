"""API подписки: лимиты, 402, счёт (TASK-026/027)."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from aiogram import Bot
from httpx import AsyncClient

from bina.application.subscriptions import Plan
from bina.infrastructure.api.routes import subscription
from bina.infrastructure.db.models.users import SubscriptionTier
from bina.infrastructure.payments import invoice
from tests.support.fakes import FakeFavoritesRepository, Store


@pytest.fixture(autouse=True)
def patch_subscription(monkeypatch: pytest.MonkeyPatch, store: Store) -> None:
    monkeypatch.setattr(
        subscription, "FavoritesRepository", lambda session: FakeFavoritesRepository(store)
    )

    class Searches:
        def __init__(self, session: Any) -> None:
            pass

        async def count_by_user(self, user_id: Any) -> int:
            return 0

    monkeypatch.setattr(subscription, "SavedSearchesRepository", Searches)


async def test_favorites_unlimited_on_free_plan(
    client: AsyncClient, store: Store, auth: dict[str, str]
) -> None:
    district = store.add_district("Ваке")
    ids = [str(store.add_listing(district).id) for _ in range(25)]
    for listing_id in ids:
        response = await client.post(
            "/api/favorites", json={"listing_id": listing_id}, headers=auth
        )
        assert response.status_code == 201


async def test_subscription_and_me(client: AsyncClient, store: Store, auth: dict[str, str]) -> None:
    body = (await client.get("/api/subscription", headers=auth)).json()
    assert body["tier"] == "free"
    assert body["limits"] == {"favorites": None, "searches": 1}
    assert body["plans"][0]["price_stars"] == 250

    user = store.users[555]
    user.subscription_tier = SubscriptionTier.NOMAD
    user.subscription_expires_at = datetime.now(UTC) - timedelta(days=1)
    me = (await client.get("/api/me", headers=auth)).json()
    assert (me["subscription_tier"], me["is_premium"], me["subscription_expires_at"]) == (
        "free",
        False,
        None,
    )


async def test_invoice_link(
    client: AsyncClient, auth: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[str, str]] = []

    async def fake_link(bot: Bot, plan: Plan, language: str) -> str:
        calls.append((plan.invoice_payload, language))
        return "https://t.me/$invoice"

    monkeypatch.setattr(invoice, "create_invoice_link", fake_link)

    response = await client.post(
        "/api/subscription/invoice", json={"plan": "premium_month"}, headers=auth
    )
    assert response.status_code == 200
    assert response.json() == {"url": "https://t.me/$invoice"}
    assert calls == [("sub:premium_month", "en")]

    missing = await client.post("/api/subscription/invoice", json={"plan": "x"}, headers=auth)
    assert missing.status_code == 404
    assert (await client.post("/api/subscription/invoice", json={"plan": "x"})).status_code == 401
