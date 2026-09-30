"""Каждая модель читается из базы целиком: миграции создали все её колонки."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bina.infrastructure.db.models import Base


async def test_every_model_selects(session: AsyncSession) -> None:
    for mapper in Base.registry.mappers:
        await session.execute(select(mapper.class_).limit(1))
