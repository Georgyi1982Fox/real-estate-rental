"""ListingsRepository на настоящем PostgreSQL."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bina.application.ports.scraper import RawListing
from bina.infrastructure.db.repositories.listings import ListingsRepository


async def test_add_skips_accepts_duplicate_ids(session: AsyncSession) -> None:
    """Одно объявление дважды в выдаче — не ошибка «cannot affect row a second time»."""
    repository = ListingsRepository(session)
    await repository.add_skips("ss", ["1", "2", "1"])
    await repository.add_skips("ss", ["2", "2"])
    await session.commit()
    since = datetime.now(UTC) - timedelta(minutes=1)
    assert await repository.recent_skips("ss", since) == {"1", "2"}


def _telegram_raw(source_id: str, photos: list[str]) -> RawListing:
    return RawListing(
        source_id=source_id,
        source_name="telegram",
        title="",
        description="Сдаётся квартира в центре",
        price=600,
        currency="USD",
        rooms=2,
        area=55.0,
        district="Ваке",
        url=f"https://t.me/{source_id}",
        photos=photos,
    )


async def test_source_remote_photos_finds_only_external_links(session: AsyncSession) -> None:
    """Выбираются только объявления Telegram с внешними ссылками на фото (не ``/api/media``)."""
    repository = ListingsRepository(session)
    remote = await repository.create_or_update_from_raw(
        _telegram_raw("chan/1", ["https://cdn4.telesco.pe/file/a.jpg"])
    )
    await repository.create_or_update_from_raw(
        _telegram_raw("chan/2", ["/api/media/listings/chan2/b.jpg"])
    )
    await repository.create_or_update_from_raw(_telegram_raw("chan/3", []))
    await session.commit()

    found = await repository.source_remote_photos("telegram", 10)

    assert [listing.id for listing in found] == [remote.id]
