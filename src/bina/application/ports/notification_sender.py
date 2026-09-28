"""Порт доставки уведомлений пользователю (Telegram) — TASK-028."""

from abc import ABC, abstractmethod
from enum import Enum

from bina.application.repositories.notifications import PendingNotification


class DeliveryResult(Enum):
    """Итог отправки."""

    SENT = "sent"
    # Доставить нельзя и не нужно пытаться снова (пользователь заблокировал бота)
    UNDELIVERABLE = "undeliverable"
    # Временная ошибка (сеть, лимиты): повторить при следующем запуске
    RETRY = "retry"


class INotificationSender(ABC):
    """Отправляет уведомление пользователю."""

    @abstractmethod
    async def send(self, pending: PendingNotification) -> DeliveryResult:
        """Отправить одно уведомление."""
