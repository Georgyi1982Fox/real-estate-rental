"""Смена языка меняет ВСЁ: заголовок, описание, адрес, владельца, район (TASK-019).

Сценарий с реального SS.ge: заголовок сайта по-русски, описание хозяин написал
по-грузински. После сохранения и перевода API отдаёт каждое поле на всех трёх
языках, и каждое — буквами своего языка.
"""

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

    # Текст лёг в колонки своего языка, а не «русской страницы»
    assert (listing.title_ru, listing.description_ka) == (RAW.title, RAW.description)
    assert (listing.description_ru, listing.title_ka) == ("", "")

    translator = ScriptTranslator()
    async with session_factory() as work:
        stats = await TranslateListingsUseCase(
            translator, ListingsRepository(work), after_save=work.commit
        ).execute(limit=10)
    assert stats.translated == 1
    # Заголовок — сначала на язык описания, потом всё — с языка описания
    assert translator.calls == [("ru", ("ka",)), ("ka", ("ru", "en"))]

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
    assert body["title"]["ru"] == RAW.title
    assert body["description"]["ka"] == RAW.description

    # Повторный запуск: переводить больше нечего
    async with session_factory() as work:
        again = await TranslateListingsUseCase(
            ScriptTranslator(), ListingsRepository(work)
        ).execute(limit=10)
    assert again.checked == 0

    # Хозяин изменил описание — переводы описания сброшены и сделаются заново
    changed = dataclasses.replace(RAW, description="ქირავდება ბინა, ახალი რემონტით.")
    updated = await repository.create_or_update_from_raw(changed)
    await session.commit()
    assert (updated.description_ru, updated.description_en) == ("", "")
    assert updated.title_ru == RAW.title
