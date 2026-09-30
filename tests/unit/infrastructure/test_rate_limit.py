"""Ограничение частоты (TASK-019): скользящее окно."""

from bina.infrastructure.ratelimit import SlidingWindowLimiter


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_sliding_window() -> None:
    clock = Clock()
    limiter = SlidingWindowLimiter(limit=2, window=10, clock=clock)
    assert limiter.hit("a") is None
    assert limiter.hit("a") is None
    assert limiter.hit("a") == 10
    assert limiter.hit("b") is None, "у каждого свой лимит"
    clock.now = 4
    assert limiter.hit("a") == 6
    clock.now = 10.5
    assert limiter.hit("a") is None


def test_disabled() -> None:
    limiter = SlidingWindowLimiter(limit=0, window=10)
    assert all(limiter.hit("a") is None for _ in range(100))
