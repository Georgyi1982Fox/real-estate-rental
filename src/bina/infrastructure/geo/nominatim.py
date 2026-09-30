"""Геокодер OpenStreetMap Nominatim (TASK-080).

Бесплатно и без ключа, но по правилам сервиса: не чаще 1 запроса в секунду и
с понятным ``User-Agent``. Ищем только в Грузии, в пределах Тбилиси.
https://operations.osmfoundation.org/policies/nominatim/
"""

import asyncio
import time

import httpx

from bina.application.district_guide import TBILISI_BOUNDS
from bina.application.ports.geocoder import GeocoderError

URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "Bina.ai/0.1 (rental search for Tbilisi; https://bina.test-realtybot.ru)"
MIN_INTERVAL = 1.1  # секунд между запросами


class NominatimGeocoder:
    """Адрес → (широта, долгота)."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            timeout=15, headers={"User-Agent": USER_AGENT, "Accept-Language": "en"}
        )
        self._last_request = 0.0

    async def locate(self, address: str, city: str) -> tuple[float, float] | None:
        wait = self._last_request + MIN_INTERVAL - time.monotonic()
        if wait > 0:
            await asyncio.sleep(wait)
        south, west, north, east = TBILISI_BOUNDS
        params = {
            "q": f"{address}, {city}",
            "format": "jsonv2",
            "limit": "1",
            "countrycodes": "ge",
            "viewbox": f"{west},{north},{east},{south}",
            "bounded": "1",
        }
        try:
            response = await self._client.get(URL, params=params)
            response.raise_for_status()
            results = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GeocoderError(str(exc)) from exc
        finally:
            self._last_request = time.monotonic()
        if not results:
            return None
        try:
            return float(results[0]["lat"]), float(results[0]["lon"])
        except (KeyError, TypeError, ValueError) as exc:
            raise GeocoderError("unexpected answer") from exc

    async def close(self) -> None:
        await self._client.aclose()
