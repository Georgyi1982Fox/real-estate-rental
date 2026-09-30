"""Промпты AI-помощника арендатора (TASK-095)."""

from bina.application.ports.assistant import ListingBrief

# Длинные описания обрезаем: суть в начале (и дешевле)
MAX_DESCRIPTION_CHARS = 2000
LANGUAGE_NAMES = {"ru": "Russian", "en": "English", "ka": "Georgian"}


def _listing_block(listing: ListingBrief) -> str:
    floor = (
        f"{listing.floor}/{listing.total_floors}"
        if listing.floor is not None and listing.total_floors
        else (str(listing.floor) if listing.floor is not None else "unknown")
    )
    return f"""Listing:
- Title: {listing.title}
- Price: {listing.price} per month
- Rooms: {listing.rooms}, area: {listing.area} m², floor: {floor}
- District: {listing.district}; address: {listing.address or "not given"}
- Amenities: {", ".join(listing.features) or "not listed"}
- Description: {listing.description[:MAX_DESCRIPTION_CHARS] or "none"}"""


def _note_block(note: str) -> str:
    return f"About the tenant (from the tenant): {note}" if note else "About the tenant: nothing."


def build_owner_message_prompt(listing: ListingBrief, language: str, note: str) -> str:
    """Сообщение хозяину: JSON с грузинским текстом и переводом."""
    target = LANGUAGE_NAMES.get(language, "English")
    return f"""You help a tenant in Georgia (Tbilisi, Batumi) write the first message to a
landlord about an apartment for long-term rent. Write a short, polite, natural message
IN GEORGIAN (Georgian script), 3-6 sentences: greeting, interest in this apartment
(mention district and price), the tenant details below if given, a request to arrange a
viewing and 1-2 key questions
(is it still available, what is included in the price). No emojis, no made-up facts.

Then translate that message into {target} for the tenant.

Reply with ONLY a JSON object, no markdown:
{{"text_ka": "...", "translation": "..."}}

{_listing_block(listing)}

{_note_block(note)}
"""


def build_viewing_questions_prompt(listing: ListingBrief, language: str, note: str) -> str:
    """Вопросы для просмотра: JSON со списком строк."""
    target = LANGUAGE_NAMES.get(language, "English")
    return f"""You help a tenant prepare for viewing an apartment for long-term rent in
Georgia (Tbilisi or Batumi). Write 5 to 8 short, practical questions to ask the landlord or
things to check during the viewing, specific to THIS listing (use its details; ask about what the
listing leaves unclear). Consider typical Georgian rental issues: heating in winter (central/gas),
utilities and who pays them, deposit and contract, hot water, noise, internet, neighbours,
pets. Use {target}. No numbering, no emojis.

Reply with ONLY a JSON object, no markdown:
{{"questions": ["...", "..."]}}

{_listing_block(listing)}

{_note_block(note)}
"""
