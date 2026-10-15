"""Промпт AI-проверки гостиницы на мошенничество (TASK-120, этап 2)."""

from bina.application.ports.fraud import AI_REASONS, HotelFacts
from bina.application.ports.translator import ListingText

# Длинные описания обрезаем: признаки мошенничества видны в начале (и дешевле)
MAX_DESCRIPTION_CHARS = 3000

# Те же коды, что у квартир, но подсказки — про краткосрочное жильё
_REASON_HINTS = {
    "prepayment": "asks for full prepayment or a card transfer before arrival, off any booking",
    "off_platform": "pushes to continue only in a messenger/e-mail, avoids a booking site or calls",
    "urgency": "pressure: 'today only', 'last room', 'pay now to reserve'",
    "too_good": "a hotel or apartment far below a realistic nightly price",
    "vague": "no real address or details, generic copy-paste text that fits any place",
    "owner_abroad": "owner is abroad / booking or keys will be sent / no in-person check-in",
}


def build_hotel_fraud_prompt(text: ListingText, facts: HotelFacts) -> str:
    """Промпт: название и описание гостиницы + факты, ответ — JSON с баллом и кодами причин."""
    reasons = "\n".join(f'- "{code}": {_REASON_HINTS[code]}' for code in AI_REASONS)
    price = (
        f"{facts.price_per_night_gel:.0f} GEL/night"
        if facts.price_per_night_gel is not None
        else "unknown"
    )
    stars = f"{facts.stars}" if facts.stars is not None else "not set"
    description = text.description[:MAX_DESCRIPTION_CHARS]
    return f"""You check short-stay accommodation listings in Georgia (hotels, guest houses,
hostels, apart-hotels) posted by their owners for scams. Most are honest. A deposit paid at
check-in, utilities, house rules, and asking to call or WhatsApp are NORMAL and not red flags.
Flag only clear scam patterns.

Red flags (use exactly these codes):
{reasons}

Score from 0 to 100: 0-20 normal listing, 40-60 some warning signs,
80-100 almost certainly a scam. Be conservative.

Reply with ONLY a JSON object, no markdown:
{{"score": 0, "reasons": []}}

Facts:
- Kind: {facts.kind}, city: {facts.city}, stars: {stars}
- Price from: {price}, sleeps up to {facts.max_guests}
- Amenities listed: {facts.amenities}, photos: {facts.photos}

Name:
{text.title}

Description:
{description}
"""
