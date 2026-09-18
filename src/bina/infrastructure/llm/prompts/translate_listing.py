from typing import NamedTuple


class TranslationPrompt(NamedTuple):
    """Промпт для перевода объявления."""
    
    title: str
    description: str
    target_language: str = "ka"  # грузинский по умолчанию
    
    def __str__(self) -> str:
        return f"""Translate the following real estate listing to {self.target_language}.

Title: {self.title}

Description: {self.description}

Return only the translated title and description in JSON format with keys "title" and "description". Do not include any other text."""