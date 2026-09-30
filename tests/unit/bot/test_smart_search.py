"""Умный поиск в чате: текст сообщения → объявления по смыслу (TASK-012)."""

from tests.support.embeddings import FakeEmbedder

from .conftest import BotHarness


def seed(harness: BotHarness) -> None:
    vake = harness.store.add_district("Ваке")
    harness.store.add_listing(vake, title_ru="Квартира у метро")
    harness.store.add_listing(vake, title_ru="Квартира с балконом")
    harness.store.add_listing(vake, title_ru="Квартира в центре")


async def test_free_text_finds_by_meaning(harness: BotHarness) -> None:
    seed(harness)
    embedder = FakeEmbedder()
    harness.dispatcher["embedder"] = embedder

    await harness.send("хочу квартиру с балконом")

    text = harness.last_text()
    assert "Умный поиск" in text
    assert text.index("Квартира с балконом") < text.index("Квартира у метро")
    assert embedder.calls == [["хочу квартиру с балконом"]]
    buttons = [b.text for row in harness.last_markup().inline_keyboard for b in row]
    assert "🏠 Главное меню" in buttons


async def test_without_ai_shows_hint(harness: BotHarness) -> None:
    seed(harness)
    await harness.send("хочу квартиру с балконом")
    assert "Не понял" in harness.last_text()


async def test_service_down_shows_hint(harness: BotHarness) -> None:
    seed(harness)
    harness.dispatcher["embedder"] = FakeEmbedder(fail=True)
    await harness.send("хочу квартиру с балконом")
    assert "Не понял" in harness.last_text()


async def test_too_short_text_is_not_a_query(harness: BotHarness) -> None:
    seed(harness)
    embedder = FakeEmbedder()
    harness.dispatcher["embedder"] = embedder
    await harness.send("ок")
    assert "Не понял" in harness.last_text()
    assert embedder.calls == []


async def test_nothing_found(harness: BotHarness) -> None:
    harness.dispatcher["embedder"] = FakeEmbedder()
    await harness.send("квартира с бассейном")
    assert "ничего не нашлось" in harness.last_text()


async def test_smart_button_explains_how_to_use(harness: BotHarness) -> None:
    """Кнопка «🧠 Умный поиск» в главном меню объясняет, что просто написать запрос."""
    from bina.infrastructure.bot.keyboards.callbacks import MenuCallback, MenuSection

    embedder = FakeEmbedder()
    harness.dispatcher["embedder"] = embedder
    await harness.send("/start")
    menu = [b.text for row in harness.last_markup().inline_keyboard for b in row]
    assert "🧠 Умный поиск" in menu

    await harness.press(MenuCallback(section=MenuSection.SMART).pack())
    assert "Напишите мне обычным сообщением" in harness.last_text()

    # Кнопка внизу чата и команда — то же самое, это не запрос поиска
    await harness.send("🧠 Умный поиск")
    assert "Напишите мне обычным сообщением" in harness.last_text()
    await harness.send("/smart")
    assert "Напишите мне обычным сообщением" in harness.last_text()
    assert embedder.calls == []


async def test_smart_button_without_ai(harness: BotHarness) -> None:
    await harness.send("/smart")
    assert "недоступен" in harness.last_text()
