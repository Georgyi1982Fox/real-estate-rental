"""Распознавание речи через OpenAI-совместимый API (OpenAI, AITUNNEL): Whisper."""

import httpx
import structlog

from bina.application.ports.speech import ISpeechToText, SpeechError

logger = structlog.get_logger(__name__)

DEFAULT_MODEL = "whisper-1"


class OpenAITranscriptionProvider(ISpeechToText):
    """``POST {base_url}/audio/transcriptions`` (multipart: файл и модель) → ``{"text": ...}``."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = client

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout, headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def transcribe(self, audio: bytes, filename: str) -> str:
        try:
            response = await self.client.post(
                f"{self.base_url}/audio/transcriptions",
                data={"model": self.model},
                files={"file": (filename, audio, "application/octet-stream")},
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Speech recognition failed", error=str(exc) or type(exc).__name__)
            raise SpeechError(str(exc) or type(exc).__name__) from exc
        text = data.get("text") if isinstance(data, dict) else None
        if not isinstance(text, str):
            raise SpeechError("no text in the response")
        return text.strip()
