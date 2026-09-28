"""AI-перевод на настоящем PostgreSQL: миграция, выборка, сохранение, сброс, API (TASK-010)."""

from collections.abc import Sequence

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bina.application.ports.scraper import RawListing
from bina.application.ports.translator import ITranslator, ListingText
from bina.application.use_cases.translate_listings import TranslateListingsUseCase
from bina.infrastructure.api.server import create_app
from bina.infrastructure.api.settings import ApiSettings
from bina.infrastructure.db.models import Listing
from bina.infrastructure.db.repositories.listings import ListingsRepository


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
