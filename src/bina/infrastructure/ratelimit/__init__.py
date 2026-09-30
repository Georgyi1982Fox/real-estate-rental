"""Ограничение частоты запросов (TASK-019): общее для API и бота."""

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

# Сколько ключей держать до очистки устаревших (защита памяти от множества IP)
MAX_KEYS = 50_000


@dataclass
class SlidingWindowLimiter:
    """Не больше ``limit`` событий за ``window`` секунд на ключ (IP, пользователя).

    Хранится в памяти процесса: у API и бота по одному процессу, этого достаточно.
    ``limit <= 0`` — без ограничения.
    """

    limit: int
    window: float
    clock: Callable[[], float] = time.monotonic
    _events: dict[str, deque[float]] = field(default_factory=dict)

    def hit(self, key: str) -> float | None:
        """Засчитать событие. ``None`` — можно; иначе сколько секунд подождать."""
        if self.limit <= 0:
            return None
        now = self.clock()
        events = self._events.setdefault(key, deque())
        while events and events[0] <= now - self.window:
            events.popleft()
        if len(events) >= self.limit:
            return max(0.0, events[0] + self.window - now)
        events.append(now)
        if len(self._events) > MAX_KEYS:
            self._prune(now)
        return None

    def _prune(self, now: float) -> None:
        stale = [
            key
            for key, events in self._events.items()
            if not events or events[-1] <= now - self.window
        ]
        for key in stale:
            del self._events[key]
