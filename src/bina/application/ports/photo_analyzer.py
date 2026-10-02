"""Порт AI-анализа фото квартиры (TASK-114)."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from bina.application.photo_analysis import PhotoReport


class PhotoAnalysisError(Exception):
    """AI не ответил или ответил не тем."""


class IPhotoAnalyzer(ABC):
    @abstractmethod
    async def analyze(self, images: Sequence[str]) -> PhotoReport:
        """Вывод по фото (адреса картинок).

        Raises:
            PhotoAnalysisError: анализ не удался.
        """
