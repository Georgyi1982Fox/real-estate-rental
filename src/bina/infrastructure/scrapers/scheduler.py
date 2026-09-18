
import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.bina.application.ports.scraper import RawListing
from src.bina.infrastructure.scrapers.deduplicator import ListingDeduplicator
from src.bina.infrastructure.scrapers.myhome_scraper import MyHomeScraper
from src.bina.infrastructure.scrapers.normalizer import ListingNormalizer
from src.bina.infrastructure.scrapers.repository import ScrapedListingsRepository
from src.bina.infrastructure.scrapers.ss_scraper import SSScraper

logger = structlog.get_logger(__name__)


class ScraperScheduler:
    """Планировщик для парсинга объявлений."""

    def __init__(
        self,
        myhome_scraper: MyHomeScraper,
        ss_scraper: SSScraper,
        normalizer: ListingNormalizer,
        deduplicator: ListingDeduplicator,
        repository: ScrapedListingsRepository,
        interval_hours: int = 6,
    ) -> None:
        self.myhome_scraper = myhome_scraper
        self.ss_scraper = ss_scraper
        self.normalizer = normalizer
        self.deduplicator = deduplicator
        self.repository = repository
        self.interval_hours = interval_hours
        self.scheduler = AsyncIOScheduler()

    def start(self) -> None:
        """Запускает планировщик."""
        logger.info("Starting scraper scheduler", interval_hours=self.interval_hours)

        # Добавляем задачи в планировщик
        self.scheduler.add_job(
            self._scrape_all_sources,
            trigger=IntervalTrigger(hours=self.interval_hours),
            id="scrape_all",
            name="Scrape all sources",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("Scraper scheduler started")

    async def stop(self) -> None:
        """Останавливает планировщик."""
        logger.info("Stopping scraper scheduler")
        self.scheduler.shutdown(wait=False)
        logger.info("Scraper scheduler stopped")

    async def scrape_myhome(self, limit: int = 50) -> int:
        """Парсит объявления с MyHome.ge."""
        logger.info("Scraping MyHome", limit=limit)
        return await self._scrape_source(self.myhome_scraper, limit)

    async def scrape_ss(self, limit: int = 50) -> int:
        """Парсит объявления с SS.ge."""
        logger.info("Scraping SS", limit=limit)
        return await self._scrape_source(self.ss_scraper, limit)

    async def scrape_all(self, limit: int = 50) -> int:
        """Парсит объявления со всех источников."""
        logger.info("Scraping all sources", limit=limit)
        return await self._scrape_all_sources(limit)

    async def _scrape_source(self, scraper, limit: int) -> int:
        """Парсит объявления из одного источника."""
        try:
            # Парсим объявления
            raw_listings = await scraper.scrape_listings(limit)
            logger.debug("Raw listings scraped", count=len(raw_listings))

            if not raw_listings:
                logger.warning("No listings scraped from source")
                return 0

            # Нормализуем объявления
            normalized_listings: list[RawListing] = []
            for listing in raw_listings:
                normalized = self.normalizer.normalize_listing(listing)
                if normalized:
                    normalized_listings.append(normalized)

            logger.debug("Normalized listings", count=len(normalized_listings))

            if not normalized_listings:
                logger.warning("No valid listings after normalization")
                return 0

            # Дедуплицируем объявления
            unique_listings = await self.deduplicator.deduplicate(normalized_listings)
            logger.debug("Unique listings after deduplication", count=len(unique_listings))

            if not unique_listings:
                logger.info("No new or updated listings to save")
                return 0

            # Сохраняем в БД
            saved_count = await self.repository.save_listings(unique_listings)
            logger.info("Scraping completed successfully", source=scraper.__class__.__name__, saved=saved_count)

            return saved_count

        except Exception as e:
            logger.error("Error scraping source", source=scraper.__class__.__name__, error=str(e))
            return 0

    async def _scrape_all_sources(self, limit: int = 50) -> int:
        """Парсит объявления со всех источников."""
        total_saved = 0

        # Парсим MyHome
        myhome_saved = await self.scrape_myhome(limit // 2)
        total_saved += myhome_saved

        # Парсим SS
        ss_saved = await self.scrape_ss(limit - (limit // 2))
        total_saved += ss_saved

        logger.info("All sources scraping completed", total_saved=total_saved)
        return total_saved
