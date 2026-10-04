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
    first = await repository.create_or_update_from_raw(raw("1", "Квартира", "Квартира в Ваке"))
    await repository.create_or_update_from_raw(raw("2", "Квартира", "Квартира в Сабуртало"))
    await session.commit()

    # Заголовки сразу на трёх языках (из данных); описание ждёт перевода
    assert first.title_ka == "2-ოთახიანი ბინა, ვაკე, 60 მ²"
    assert (first.description_ka, first.description_en) == ("", "")
    assert len(await repository.list_untranslated(10)) == 2

    translator = EchoTranslator()
    stats = await TranslateListingsUseCase(translator, repository).execute(limit=10)
    await session.commit()
    assert (stats.translated, stats.failed, translator.calls) == (2, 0, 2)
    assert await repository.list_untranslated(10) == []

    session.expire_all()
    listing = await repository.find_by_source("1", "ss")
    assert isinstance(listing, Listing)
    assert listing.description_ka == "[ka] Квартира в Ваке"
    assert listing.title_ka == "2-ოთახიანი ბინა, ვაკე, 60 მ²", "заголовок перевод не трогает"

    # Повторный парсинг того же текста перевод не трогает
    await repository.create_or_update_from_raw(raw("1", "Квартира", "Квартира в Ваке"))
    await session.commit()
    assert await repository.list_untranslated(10) == []

    # Владелец изменил текст — старый перевод описания сброшен и будет сделан заново
    await repository.create_or_update_from_raw(
        raw("1", "Квартира", "Квартира в Ваке, после ремонта")
    )
    await session.commit()
    pending = await repository.list_untranslated(10)
    assert [item.source_id for item in pending] == ["1"]
    assert (pending[0].description_ka, pending[0].description_en) == ("", "")
    assert pending[0].title_en == "2-room apartment, Vake, 60 m²"

    # API отдаёт все три языка
    await TranslateListingsUseCase(translator, repository).execute(limit=10)
    await session.commit()
    app = create_app(ApiSettings(), session_factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        body = (await client.get(f"/api/listings/{listing.id}")).json()
    assert body["title"] == {
        "ka": "2-ოთახიანი ბინა, ვაკე, 60 მ²",
        "ru": "2-комн. квартира, Ваке, 60 м²",
        "en": "2-room apartment, Vake, 60 m²",
    }
    assert body["description"] == {
        "ka": "[ka] Квартира в Ваке, после ремонта",
        "ru": "Квартира в Ваке, после ремонта",
        "en": "[en] Квартира в Ваке, после ремонта",
    }


async def test_each_translation_is_committed(
    session: AsyncSession, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Перевод сохраняется сразу: сбой на следующем объявлении его не откатывает."""
    repository = ListingsRepository(session)
    await repository.create_or_update_from_raw(raw("1", "Квартира", "Первая"))
    await repository.create_or_update_from_raw(raw("2", "Квартира", "Вторая"))
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


async def test_wrong_language_texts_are_fixed(session: AsyncSession) -> None:
    """Русское описание с грузинским названием района не попадает в грузинскую колонку;
    старый такой текст переносится на место, а грузинский перевод делается заново."""
    repository = ListingsRepository(session)
    mixed = await repository.create_or_update_from_raw(
        raw("mix", "Квартира", "Светлая квартира в районе ვაკე, рядом парк и метро")
    )
    assert mixed.description_ru.startswith("Светлая") and not mixed.description_ka

    broken = await repository.create_or_update_from_raw(raw("old", "Квартира", "Описание"))
    broken.description_ka = "Русский текст, который по ошибке лежит в грузинском поле"
    broken.description_ru = ""
    broken.title_ka = "ბინა ვაკეში"
    await session.commit()

    assert await repository.fix_wrong_languages(100) == 1
    await session.commit()
    await session.refresh(broken)
    assert broken.description_ka == "", "чужой текст убран — его переведёт AI"
    assert broken.description_ru.startswith("Русский текст"), "текст перенесён на свой язык"
    assert broken.title_ka == "ბინა ვაკეში", "правильный текст не трогаем"
    assert await repository.fix_wrong_languages(100) == 0


async def test_failed_translation_waits_a_day(session: AsyncSession) -> None:
    repository = ListingsRepository(session)
    hard = await repository.create_or_update_from_raw(raw("hard", "Квартира"))
    easy = await repository.create_or_update_from_raw(raw("easy", "Квартира"))
    await session.commit()

    await repository.mark_translation_failed(hard.id)
    await session.commit()
    assert [item.id for item in await repository.list_untranslated(10)] == [easy.id]
