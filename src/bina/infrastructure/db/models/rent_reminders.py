"""Напоминания об оплате аренды (TASK-109)."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class RentReminder(Base):
    """День оплаты и сумма; когда уже напоминали и за какой срок отмечена оплата."""

    __tablename__ = "bina_rent_reminders"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bina_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GEL")
    # Дата оплаты, отмеченная «Оплачено»; до неё напоминаний нет
    paid_for: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Когда (по Тбилиси) последний раз напомнили — не чаще раза в день
    last_reminded_on: Mapped[date | None] = mapped_column(Date, nullable=True)
