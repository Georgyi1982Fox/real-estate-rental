"""Промпт разбора объявления из Telegram-поста (TASK-091)."""

from bina.application.listing_details import FEATURES

# Посты длинные редко; обрезаем на всякий случай (и дешевле)
MAX_TEXT_CHARS = 3000


def build_extract_prompt(text: str) -> str:
    """Промпт: текст поста, ответ — JSON с полями квартиры."""
    features = ", ".join(FEATURES)
    return f"""You read posts from Telegram channels about apartments in Georgia.
Extract the listing data from the post below.

"is_rental_offer" is true ONLY for an offer to rent out an apartment: monthly or daily.
It is false for: sale, someone LOOKING for an apartment ("ищу", "сниму"),
houses/offices/commercial property, ads and channel news.
"daily" is true for daily/short-term rent with a price per day ("посуточно", "daily",
"დღიურად"), false for monthly rent.

Rules:
- "city": in English: "Tbilisi", "Batumi", "Kutaisi", ... (null if not stated; a Tbilisi
  district like Vake or Saburtalo means Tbilisi).
- "district": district name as written in the post (e.g. "Ваке", "Saburtalo", "ვაკე").
- "price": rent as a number (per month, or per day if "daily");
  "currency": "USD", "GEL" or "EUR" ($ = USD, ₾ or лари = GEL).
- "rooms": total rooms. "2-комнатная" = 2 rooms. "1+1" = 2 rooms, "2+1" = 3 rooms.
  "bedrooms": number of bedrooms if stated.
- "area": m². "floor" and "total_floors": "5/9 этаж" = floor 5 of 9.
- "phone": phone number as written, if present.
- "features": only codes from this list that the post clearly mentions: {features}.
- "title": a short title in the language of the post, e.g. "2-комн. квартира в Ваке, 60 м²".
- Use null for anything not in the post. Do not guess.

Reply with ONLY a JSON object, no markdown:
{{"is_rental_offer": true, "daily": false, "city": "Tbilisi", "district": "Ваке", "price": 800,
"currency": "USD", "rooms": 2, "bedrooms": 1, "area": 60, "floor": 5, "total_floors": 9,
"address": null, "phone": null, "features": ["furniture"], "title": "2-комн. квартира в Ваке"}}

Post:
{text[:MAX_TEXT_CHARS]}
"""
