"""Распознавание речи: голосовое сообщение → текст (умный поиск голосом)."""

from abc import ABC, abstractmethod


class SpeechError(Exception):
    """Сервис распознавания не ответил или ответил не тем."""


class ISpeechToText(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, filename: str) -> str:
        """Текст из аудио (язык определяется сам).

        Raises:
            SpeechError: распознать не удалось.
        """
