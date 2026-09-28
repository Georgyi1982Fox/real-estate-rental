"""AI-перевод на настоящем PostgreSQL: миграция, выборка, сохранение, сброс, API (TASK-010)."""

from collections.abc import Sequence

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from bina.application.ports.scraper import RawListing
from bina.application.ports.translator import ITranslator, ListingText
from bina.application.use_cases.translate_listings import TranslateListingsUseCase
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.locks import TRANSLATE_LOCK, advisory_lock
from bina.infrastructure.db.models import Listing
from bina.infrastructure.db.repositories.listings import ListingsRepository
from bina.infrastructure.llm.llm_factory import LLMFactory
from bina.infrastructure.scrapers import cli as scrape_cli
from tests.integration.conftest import DATABASE_URL


def raw(source_id: str, title: str, description: str = "Описание") -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name="ss",
        title=title,
        description=description,
        price=1500.0,
        currency="GEL",
        rooms=2,
        area=60.0,
        district="Ваке",
        url=f"https://home.ss.ge/ru/{source_id}",
    )


class EchoTranslator(ITranslator):
    """Перевод = префикс языка; считает вызовы."""

    def __init__(self) -> None:
        self.calls = 0

    async def translate(
        self, text: ListingText, source: str, targets: Sequence[str]
    ) -> dict[str, ListingText]:
        self.calls += 1
        return {
            code: ListingText(f"[{code}] {text.title}", f"[{code}] {text.description}")
            for code in targets
        }


async def test_translate_save_reset_and_api(
    session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    repository = ListingsRepository(session)
    first = await repository.create_or_update_from_raw(raw("1", "Квартира в Ваке"))
    await repository.create_or_update_from_raw(raw("2", "Квартира в Сабуртало"))
    await session.commit()

    # Новые объявления: английский и грузинский пустые (server_default миграции)
    assert (first.title_ka, first.title_en, first.description_en) == ("", "", "")
    assert len(await repository.list_untranslated(10)) == 2

    translator = EchoTranslator()
    stats = await TranslateListingsUseCase(translator, repository).execute(limit=10)
    await session.commit()
    assert (stats.translated, stats.failed, translator.calls) == (2, 0, 2)
    assert await repository.list_untranslated(10) == []

    session.expire_all()
    listing = await repository.find_by_source("1", "ss")
    assert isinstance(listing, Listing)
    assert listing.title_ka == "[ka] Квартира в Ваке"
    assert listing.description_en == "[en] Описание"

    # Повторный парсинг того же текста перевод не трогает
    await repository.create_or_update_from_raw(raw("1", "Квартира в Ваке"))
    await session.commit()
    assert await repository.list_untranslated(10) == []

    # Владелец изменил текст — старый перевод сброшен и будет сделан заново
    await repository.create_or_update_from_raw(raw("1", "Квартира в Ваке, после ремонта"))
    await session.commit()
    pending = await repository.list_untranslated(10)
    assert [item.source_id for item in pending] == ["1"]
    assert (pending[0].title_ka, pending[0].title_en) == ("", "")

    # API отдаёт все три языка
    await TranslateListingsUseCase(translator, repository).execute(limit=10)
    await session.commit()
    app = create_app(ApiSettings(), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get(f"/api/listings/{listing.id}")).json()
    assert body["title"] == {
        "ka": "[ka] Квартира в Ваке, после ремонта",
        "ru": "Квартира в Ваке, после ремонта",
        "en": "[en] Квартира в Ваке, после ремонта",
    }


async def test_each_translation_is_committed(
    session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Перевод сохраняется сразу: сбой на следующем объявлении его не откатывает."""
    repository = ListingsRepository(session)
    await repository.create_or_update_from_raw(raw("1", "Первая"))
    await repository.create_or_update_from_raw(raw("2", "Вторая"))
    await session.commit()

    class FailSecond(EchoTranslator):
        async def translate(
            self, text: ListingText, source: str, targets: Sequence[str]
        ) -> dict[str, ListingText]:
            if self.calls == 1:
                raise RuntimeError("AI is down")
            return await super().translate(text, source, targets)

    async with session_factory() as work:
        use_case = TranslateListingsUseCase(
            FailSecond(), ListingsRepository(work), after_save=work.commit
        )
        with pytest.raises(RuntimeError):
            await use_case.execute(limit=10)
        await work.rollback()

    async with session_factory() as check:
        pending = await ListingsRepository(check).list_untranslated(10)
    assert len(pending) == 1, "первый перевод сохранён, несмотря на сбой на втором"


async def test_only_one_translation_at_a_time(
    engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Второй запуск перевода (другой процесс) не стартует, пока идёт первый."""
    assert DATABASE_URL
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.setattr(LLMFactory, "create_provider", staticmethod(lambda: object()))
    monkeypatch.setattr(scrape_cli, "LLMTranslator", lambda provider: EchoTranslator())

    async with advisory_lock(engine, TRANSLATE_LOCK) as first:
        assert first
        async with advisory_lock(engine, TRANSLATE_LOCK) as second:
            assert not second
        with pytest.raises(scrape_cli.TranslationBusyError):
            await scrape_cli.translate(10)

    # Блокировка снята — перевод запускается
    stats = await scrape_cli.translate(10)
    assert stats.checked == 0
