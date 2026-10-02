"""Распознавание голосовых через OpenAI-совместимый API (Whisper)."""

import httpx
import pytest

from bina.application.ports.speech import SpeechError
from bina.infrastructure.llm.providers.openai_transcription_provider import (
    OpenAITranscriptionProvider,
)


def provider(handler: httpx.MockTransport) -> OpenAITranscriptionProvider:
    client = httpx.AsyncClient(transport=handler)
    return OpenAITranscriptionProvider("key", base_url="https://ai.test/v1/", client=client)


async def test_sends_audio_and_returns_text() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"text": " двушка в Ваке \n"})

    text = await provider(httpx.MockTransport(handle)).transcribe(b"OggS", "voice.ogg")

    assert text == "двушка в Ваке"
    [request] = seen
    assert str(request.url) == "https://ai.test/v1/audio/transcriptions"
    body = request.content
    assert b'name="model"' in body and b"whisper-1" in body
    assert b'filename="voice.ogg"' in body and b"OggS" in body


@pytest.mark.parametrize(
    "response",
    [httpx.Response(500, text="down"), httpx.Response(200, json={"error": "no"})],
)
async def test_errors_raise_speech_error(response: httpx.Response) -> None:
    with pytest.raises(SpeechError):
        await provider(httpx.MockTransport(lambda _: response)).transcribe(b"x", "voice.ogg")
