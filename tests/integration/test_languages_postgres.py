"""Смена языка меняет ВСЁ: заголовок, описание, адрес, владельца, район (TASK-019).

Сценарий с реального SS.ge: заголовок сайта по-русски, описание хозяин написал
по-грузински. После сохранения и перевода API отдаёт каждое поле на всех трёх
языках, и каждое — буквами своего языка.
"""

import asyncio
import dataclasses
from collections.abc import Sequence

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.localization import script_of
from bina.application.ports.scraper import RawListing
from bina.application.ports.translator import ITranslator, ListingText
from bina.application.use_cases.translate_listings import TranslateListingsUseCase
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.repositories.listings import ListingsRepository

LANGS = ("ka", "ru", "en")
# «Перевод» буквами нужного языка (настоящий AI тоже пишет на языке перевода)
WORDS = {"ka": "ბინა ვაკეში", "ru": "Квартира в Ваке", "en": "Apartment in Vake"}


class ScriptTranslator(ITranslator):
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    async def translate(
        self, text: ListingText, source: str, targets: Sequence[str]
    ) -> dict[str, ListingText]:
        self.calls.append((source, tuple(targets)))
        return {
            code: ListingText(WORDS[code], f"{WORDS[code]} — {code}" if text.description else "")
            for code in targets
        }


RAW = RawListing(
    source_id="36999999",
    source_name="ss",
    title="Аренда 3-комнатная Квартира. Сабуртало",
    description="ქირავდება ახალი აშენებული ბინა 70 კვ.მ ფართობით.",
    price=1500,
    currency="GEL",
    rooms=3,
    area=70,
    district="Сабуртало",
    url="https://home.ss.ge/ru/36999999",
    owner_name="ნინო",
    address="ул. Мириан Мефе 19",
    features=["furniture"],
    has_details=True,
)


# Заголовок из данных (bina.application.listing_titles)
TITLE_RU = "3-комн. квартира, Сабуртало, 70 м²"


def assert_all_languages(value: dict[str, str], field: str) -> None:
    assert set(value) == set(LANGS), f"{field}: нет языков {set(LANGS) - set(value)}"
    for lang in LANGS:
        assert value[lang].strip(), f"{field}[{lang}] пустой"
        assert script_of(value[lang]) == lang, f"{field}[{lang}] не тем алфавитом: {value[lang]}"


async def test_every_field_in_every_language(
    session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    repository = ListingsRepository(session)
    listing = await repository.create_or_update_from_raw(RAW)
    await session.commit()
    listing_id = listing.id

    # Описание легло в колонку своего языка, а не «русской страницы»;
    # заголовок собран из данных сразу на трёх языках
    assert (listing.title_ru, listing.description_ka) == (TITLE_RU, RAW.description)
    assert listing.description_ru == ""
    assert script_of(listing.title_ka) == "ka" and script_of(listing.title_en) == "en"

    assert await repository.language_coverage() == (1, 1)

    translator = ScriptTranslator()
    async with session_factory() as work:
        stats = await TranslateListingsUseCase(
            translator, ListingsRepository(work), after_save=work.commit
        ).execute(limit=10)
    assert stats.translated == 1
    # Один запрос: описание — с языка описания на остальные (заголовки уже есть)
    assert translator.calls == [("ka", ("ru", "en"))]

    app = create_app(ApiSettings(), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get(f"/api/listings/{listing_id}")).json()
        districts = {
            d["id"]: d["name"] for d in (await client.get("/api/districts")).json()["items"]
        }

    assert_all_languages(body["title"], "title")
    assert_all_languages(body["description"], "description")
    assert_all_languages(body["address"], "address")
    assert_all_languages(body["owner"]["name"], "owner")
    assert_all_languages(districts[body["district"]], "district")
    # Текст сайта не заменён переводом
    assert body["title"]["ru"] == TITLE_RU
    assert body["description"]["ka"] == RAW.description

    # Повторный запуск: переводить больше нечего
    async with session_factory() as work:
        again = await TranslateListingsUseCase(
            ScriptTranslator(), ListingsRepository(work)
        ).execute(limit=10)
    assert again.checked == 0
    assert await ListingsRepository(session).language_coverage() == (1, 0)

    # Хозяин изменил описание — переводы описания сброшены и сделаются заново
    changed = dataclasses.replace(RAW, description="ქირავდება ბინა, ახალი რემონტით.")
    updated = await repository.create_or_update_from_raw(changed)
    await session.commit()
    assert (updated.description_ru, updated.description_en) == ("", "")
    assert updated.title_ru == TITLE_RU


class SlowTranslator(ScriptTranslator):
    """Как ScriptTranslator, но «думает» 50 мс и считает одновременные запросы."""

    def __init__(self) -> None:
        super().__init__()
        self.running = 0
        self.max_running = 0

    async def translate(
        self, text: ListingText, source: str, targets: Sequence[str]
    ) -> dict[str, ListingText]:
        self.running += 1
        self.max_running = max(self.max_running, self.running)
        try:
            await asyncio.sleep(0.05)
            return await super().translate(text, source, targets)
        finally:
            self.running -= 1


async def test_parallel_translation_saves_everything(
    session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Перевод по 5 объявлений одновременно: всё сохранено, ничего не потеряно."""
    repository = ListingsRepository(session)
    for n in range(12):
        await repository.create_or_update_from_raw(
            dataclasses.replace(RAW, source_id=f"p{n}", url=f"https://home.ss.ge/ru/p{n}")
        )
    await session.commit()
    assert await repository.language_coverage() == (12, 12)

    translator = SlowTranslator()
    async with session_factory() as work:
        stats = await TranslateListingsUseCase(
            translator, ListingsRepository(work), after_save=work.commit, concurrency=5
        ).execute(limit=20)

    assert (stats.checked, stats.translated, stats.failed) == (12, 12, 0)
    assert translator.max_running == 5
    async with session_factory() as check:
        assert await ListingsRepository(check).language_coverage() == (12, 0)
