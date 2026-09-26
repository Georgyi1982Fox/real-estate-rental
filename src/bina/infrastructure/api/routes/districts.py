"""Районы."""

from fastapi import APIRouter

from bina.infrastructure.api.dependencies import SessionDep
from bina.infrastructure.api.schemas import DistrictOut, DistrictsOut
from bina.infrastructure.db.repositories.districts import DistrictsRepository

router = APIRouter(prefix="/api/districts", tags=["districts"])


@router.get("", response_model=DistrictsOut)
async def list_districts(session: SessionDep) -> DistrictsOut:
    """Все районы (для фильтра и названий в карточках)."""
    districts = await DistrictsRepository(session).list_all()
    return DistrictsOut(items=[DistrictOut.from_model(district) for district in districts])
