from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = structlog.get_logger(__name__)


class ScraperScheduler:
    """Периодический запуск парсинга (первый запуск сразу)."""

    def __init__(self, job: Callable[[], Awaitable[None]], interval_hours: int = 6) -> None:
        self.job = job
        self.interval_hours = interval_hours
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        """Запускает планировщик."""
        self.scheduler.add_job(
            self.job,
            trigger=IntervalTrigger(hours=self.interval_hours),
            id="scrape_all",
            name="Scrape all sources",
            replace_existing=True,
            next_run_time=datetime.now(UTC),
            max_instances=1,
        )
        self.scheduler.start()
        logger.info("Scraper scheduler started", interval_hours=self.interval_hours)

    async def stop(self) -> None:
        """Останавливает планировщик."""
        self.scheduler.shutdown(wait=False)
        logger.info("Scraper scheduler stopped")
