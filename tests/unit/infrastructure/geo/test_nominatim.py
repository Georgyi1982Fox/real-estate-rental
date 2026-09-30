"""Геокодер OpenStreetMap Nominatim (TASK-080)."""

import httpx
import pytest

from bina.application.ports.geocoder import GeocoderError
from bina.infrastructure.geo import nominatim
from bina.infrastructure.geo.nominatim import NominatimGeocoder


@pytest.fixture(autouse=True)
def no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nominatim, "MIN_INTERVAL", 0)


def geocoder(handler: httpx.MockTransport) -> NominatimGeocoder:
    return NominatimGeocoder(httpx.AsyncClient(transport=handler))


async def test_locate() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=[{"lat": "41.7090", "lon": "44.7580"}])

    assert await geocoder(httpx.MockTransport(handle)).locate("Paliashvili 1", "Tbilisi") == (
        41.709,
        44.758,
    )
    params = requests[0].url.params
    assert params["q"] == "Paliashvili 1, Tbilisi"
    assert params["countrycodes"] == "ge"
    assert params["bounded"] == "1"


async def test_not_found() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
    assert await geocoder(transport).locate("Nowhere", "Tbilisi") is None


@pytest.mark.parametrize(
    "response",
    [httpx.Response(503), httpx.Response(200, text="oops"), httpx.Response(200, json=[{}])],
)
async def test_errors(response: httpx.Response) -> None:
    transport = httpx.MockTransport(lambda request: response)
    with pytest.raises(GeocoderError):
        await geocoder(transport).locate("Paliashvili 1", "Tbilisi")


def test_user_agent() -> None:
    assert "Bina.ai" in nominatim.USER_AGENT
