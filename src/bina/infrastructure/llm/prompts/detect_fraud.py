"""Промпт AI-проверки объявления на мошенничество (TASK-011)."""

from bina.application.ports.fraud import AI_REASONS, ListingFacts
from bina.application.ports.translator import ListingText

# Длинные описания обрезаем: признаки мошенничества видны в начале (и дешевле)
MAX_DESCRIPTION_CHARS = 3000

_REASON_HINTS = {
    "prepayment": "asks for prepayment, deposit or a card transfer before a viewing",
    "off_platform": "pushes to continue only in a messenger/e-mail, avoids calls or viewings",
    "urgency": "pressure: 'today only', 'many people want it', 'pay now to reserve'",
    "too_good": "luxury or large apartment for an unrealistically low price",
    "vague": "no address or details, generic copy-paste text that fits any flat",
    "owner_abroad": "owner is abroad / keys will be sent / no viewing possible",
}


def build_fraud_prompt(text: ListingText, facts: ListingFacts) -> str:
    """Промпт: текст объявления + факты, ответ — JSON с баллом и кодами причин."""
    reasons = "\n".join(f'- "{code}": {_REASON_HINTS[code]}' for code in AI_REASONS)
    per_m2 = f"{facts.price / facts.area:.1f}" if facts.area > 0 else "unknown"
    median = (
        f"{facts.district_median_per_m2:.1f} {facts.currency}/m²"
        if facts.district_median_per_m2 is not None
        else "unknown"
    )
    description = text.description[:MAX_DESCRIPTION_CHARS]
    return f"""You check long-term apartment rental listings in Tbilisi, Georgia, for scams.
Most listings are honest. Agencies, "no agencies" notes, commission, a deposit paid at
signing, utilities, and asking to call or WhatsApp are NORMAL and not red flags.
Flag only clear scam patterns.

Red flags (use exactly these codes):
{reasons}

Score from 0 to 100: 0-20 normal listing, 40-60 some warning signs,
80-100 almost certainly a scam. Be conservative.

Reply with ONLY a JSON object, no markdown:
{{"score": 0, "reasons": []}}

Facts:
- Price: {facts.price} {facts.currency} per month, {per_m2} {facts.currency}/m²
- District median price: {median}
- Rooms: {facts.rooms}, area: {facts.area} m², district: {facts.district or "unknown"}
- Photos: {facts.photos}

Title:
{text.title}

Description:
{description}
"""
