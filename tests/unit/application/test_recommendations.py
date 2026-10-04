"""«Вам может понравиться» и «Поделиться» (TASK-076, TASK-073): чистые правила."""

from decimal import Decimal
from uuid import UUID, uuid4

from bina.application.recommendations import pick, score, taste_of
from bina.application.sharing import listing_from_share, share_link, telegram_share_url
from bina.infrastructure.db.models import Listing

VAKE, SABURTALO, OLD_BATUMI = uuid4(), uuid4(), uuid4()
CITIES = {VAKE: "tbilisi", SABURTALO: "tbilisi", OLD_BATUMI: "batumi"}


def flat(district: UUID, rooms: int, price: int, currency: str = "GEL") -> Listing:
    return Listing(
        id=uuid4(),
        district_id=district,
        rooms=rooms,
        price=Decimal(price),
        currency=currency,
        rent_period="monthly",
    )


def test_taste_and_ranking() -> None:
    favorites = [flat(VAKE, 2, 1500), flat(VAKE, 2, 1700), flat(SABURTALO, 3, 1600)]
    taste = taste_of(favorites, CITIES)
    assert taste is not None
    assert (taste.city, taste.rent_period) == ("tbilisi", "monthly")
    assert taste.district_ids == {VAKE, SABURTALO} and taste.rooms == {2, 3}
    assert taste.price_gel == Decimal(1600)

    same_area = flat(VAKE, 2, 1600)
    in_dollars = flat(VAKE, 2, 600, "USD")  # ≈ 1620 ₾ — тоже близко
    far_and_pricey = flat(uuid4(), 6, 9000)
    assert score(same_area, taste) > score(far_and_pricey, taste)
    assert score(in_dollars, taste) > 6

    picked = pick(
        [far_and_pricey, favorites[0], same_area, in_dollars],
        taste,
        exclude={favorites[0].id},
        limit=5,
    )
    assert picked[:2] == [same_area, in_dollars], "избранное не предлагаем, лучшие сверху"
    assert far_and_pricey not in picked, "совсем не похожее не показываем"


def test_no_favorites_no_taste() -> None:
    assert taste_of([], CITIES) is None


def test_share_link_round_trip() -> None:
    listing_id = uuid4()
    link = share_link("bina_bot", listing_id)
    assert link == f"https://t.me/bina_bot?start=l_{listing_id.hex}"
    payload = link.split("start=")[1]
    assert len(payload) <= 64, "ограничение Telegram на /start"
    assert listing_from_share(payload) == listing_id
    assert listing_from_share("chat_123") is None and listing_from_share("l_bad") is None
    share = telegram_share_url(link, "Квартира · 1 500 ₾")
    assert share.startswith("https://t.me/share/url?url=https%3A%2F%2Ft.me%2Fbina_bot")
