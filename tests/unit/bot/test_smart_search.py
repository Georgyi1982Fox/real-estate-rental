"""Умный поиск в чате: текст сообщения → объявления по смыслу (TASK-012)."""

from datetime import UTC, datetime
from typing import Any

import pytest
from aiogram.types import Chat, Message, Update, Voice

from bina.application.ports.speech import ISpeechToText, SpeechError
from tests.support.embeddings import FakeEmbedder
from tests.support.telegram import CHAT_ID

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


# --- голосовые


class FakeSpeech(ISpeechToText):
    def __init__(self, text: str = "", fail: bool = False) -> None:
        self.text = text
        self.fail = fail
        self.calls: list[bytes] = []

    async def transcribe(self, audio: bytes, filename: str) -> str:
        self.calls.append(audio)
        if self.fail:
            raise SpeechError("down")
        return self.text


async def send_voice(harness: BotHarness, duration: int = 5) -> None:
    await harness.dispatcher.feed_update(
        harness.bot,
        Update(
            update_id=900,
            message=Message(
                message_id=901,
                date=datetime.now(UTC),
                chat=Chat(id=CHAT_ID, type="private"),
                from_user=harness.telegram_user,
                voice=Voice(file_id="voice-1", file_unique_id="v1", duration=duration),
            ),
        ),
    )


@pytest.fixture
def voice_download(monkeypatch: pytest.MonkeyPatch) -> None:
    from bina.infrastructure.bot.handlers import fallback

    async def download(bot: Any, file_id: str) -> bytes:
        return b"OggS-audio"

    monkeypatch.setattr(fallback, "download_voice", download)


async def test_voice_message_searches_by_meaning(harness: BotHarness, voice_download: None) -> None:
    seed(harness)
    embedder = FakeEmbedder()
    speech = FakeSpeech("хочу квартиру с балконом")
    harness.dispatcher["embedder"] = embedder
    harness.dispatcher["speech"] = speech

    await send_voice(harness)

    texts = harness.sent_texts()
    assert "Вы сказали: «<i>хочу квартиру с балконом</i>»" in texts[-2]
    assert "Умный поиск" in texts[-1]
    assert speech.calls == [b"OggS-audio"]
    assert embedder.calls == [["хочу квартиру с балконом"]]


async def test_voice_not_recognized(harness: BotHarness, voice_download: None) -> None:
    harness.dispatcher["embedder"] = FakeEmbedder()
    harness.dispatcher["speech"] = FakeSpeech(fail=True)
    await send_voice(harness)
    assert "Не получилось разобрать голосовое" in harness.last_text()


async def test_voice_too_long(harness: BotHarness, voice_download: None) -> None:
    speech = FakeSpeech("квартира")
    harness.dispatcher["embedder"] = FakeEmbedder()
    harness.dispatcher["speech"] = speech
    await send_voice(harness, duration=120)
    assert "длинновато" in harness.last_text()
    assert speech.calls == []


async def test_voice_without_ai(harness: BotHarness) -> None:
    await send_voice(harness)
    assert "Голосовые сейчас не распознаются" in harness.last_text()
