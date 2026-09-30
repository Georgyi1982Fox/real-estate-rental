"""Соглашение и политика конфиденциальности (TASK-089)."""

import re

import pytest

from bina.application.legal import DOCUMENTS, LegalDoc, legal_document, version_label
from bina.application.localization import script_of

# Названия сервисов и команды не переводятся
_KEEP = r"Bina\.ai|Premium|Telegram Stars|Telegram|Cloudflare|OpenStreetMap|/\w+"


def test_every_document_has_all_languages_and_same_structure() -> None:
    for doc, texts in DOCUMENTS.items():
        assert set(texts) == {"ru", "en", "ka"}, doc
        assert len({len(document.sections) for document in texts.values()}) == 1, doc


@pytest.mark.parametrize("doc", list(LegalDoc))
@pytest.mark.parametrize("language", ["ru", "en", "ka"])
def test_documents_are_in_their_language(doc: LegalDoc, language: str) -> None:
    """Весь текст — буквами своего языка (TASK-116)."""
    document = legal_document(doc, language)
    parts = [document.title, document.intro, version_label(language)]
    for section in document.sections:
        parts += [section.title, section.text]
    for part in parts:
        letters = re.sub(_KEEP, "", part)
        assert script_of(letters) == language, part


def test_unknown_language_falls_back_to_russian() -> None:
    assert legal_document(LegalDoc.TERMS, "de") is DOCUMENTS[LegalDoc.TERMS]["ru"]


def test_terms_mention_refunds_and_paysupport() -> None:
    """Для оплаты звёздами Telegram требует условия и путь к поддержке."""
    for document in DOCUMENTS[LegalDoc.TERMS].values():
        assert any("/paysupport" in section.text for section in document.sections)
