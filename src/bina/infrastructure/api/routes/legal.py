"""Соглашение и политика конфиденциальности для Mini App (TASK-089).

``GET /api/legal/terms`` и ``GET /api/legal/privacy`` — без авторизации
(ссылки открываются и до входа). Язык — параметр ``lang`` (ka/ru/en).
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from bina.application.legal import VERSION, LegalDoc, legal_document, version_label

router = APIRouter(prefix="/api/legal", tags=["legal"])


class LegalSectionOut(BaseModel):
    title: str
    text: str


class LegalDocumentOut(BaseModel):
    """Документ на выбранном языке."""

    doc: LegalDoc
    language: str
    title: str
    version: str = Field(description="Дата редакции, ``2026-09-30``")
    version_label: str = Field(description="«Редакция от 30.09.2026» на языке документа")
    intro: str
    sections: list[LegalSectionOut]


@router.get("/{doc}", response_model=LegalDocumentOut)
async def get_legal_document(
    doc: LegalDoc,
    lang: Annotated[Literal["ka", "ru", "en"], Query()] = "ka",
) -> LegalDocumentOut:
    """Пользовательское соглашение (``terms``) или политика конфиденциальности (``privacy``)."""
    document = legal_document(doc, lang)
    return LegalDocumentOut(
        doc=doc,
        language=lang,
        title=document.title,
        version=VERSION.isoformat(),
        version_label=version_label(lang),
        intro=document.intro,
        sections=[LegalSectionOut(title=s.title, text=s.text) for s in document.sections],
    )
