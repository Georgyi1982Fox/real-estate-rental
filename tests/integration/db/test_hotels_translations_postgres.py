"""HotelsRepository: выбор гостиниц без перевода и сохранение описаний (PostgreSQL)."""

from sqlalchemy.ext.asyncio import AsyncSession

from bina.infrastructure.db.models import Hotel
from bina.infrastructure.db.repositories.hotels import HotelsRepository
from bina.infrastructure.db.repositories.users import UsersRepository


def _hotel(owner_id: object, name: str, **descriptions: str) -> Hotel:
    values = {f"description_{code}": "" for code in ("ru", "ka", "en")}
    values.update(descriptions)
    return Hotel(
        owner_user_id=owner_id,
        kind="hotel",
        name=name,
        city="batumi",
        amenities=[],
        images=[],
        fraud_reasons=[],
        **values,
    )


async def test_list_untranslated_and_save_descriptions(session: AsyncSession) -> None:
    hotels = HotelsRepository(session)
    owner = await UsersRepository(session).create(5001, "ru")
    partial = _hotel(owner.id, "Partial", description_ru="Уютный дом у моря")
    full = _hotel(owner.id, "Full", description_ru="ru", description_ka="ka", description_en="en")
    blank = _hotel(owner.id, "Blank")
    hidden = _hotel(owner.id, "Hidden", description_ru="скрытый")
    session.add_all([partial, full, blank, hidden])
    await session.flush()
    await hotels.hide(hidden.id)
    await session.flush()

    found = await hotels.list_untranslated(10)

    # Только гостиница с описанием не на всех языках и не скрытая
    assert [h.id for h in found] == [partial.id]

    await hotels.save_descriptions(partial.id, {"ka": "ზღვისპირა სახლი", "en": "Seaside house"})
    await session.flush()
    await session.refresh(partial)
    assert partial.description_ka == "ზღვისპირა სახლი"
    assert partial.description_en == "Seaside house"
    # Исходный язык не затёрт
    assert partial.description_ru == "Уютный дом у моря"
    # Переведённая гостиница больше не выбирается
    assert await hotels.list_untranslated(10) == []
