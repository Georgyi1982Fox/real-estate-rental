"""Сертификат электронной подписи (TASK-115): грузинский + второй язык, как договор."""

from datetime import datetime

from bina.application.rent_reminders import TBILISI
from bina.application.signing import Signer
from bina.infrastructure.documents.pdf import (
    FONT,
    bilingual_table,
    heading,
    new_pdf,
    small_print,
    to_bytes,
)

TITLES = {
    "ka": "ელექტრონული ხელმოწერის სერტიფიკატი",
    "ru": "Сертификат электронной подписи",
    "en": "Electronic signature certificate",
}
LABELS = {
    "document": {"ka": "დოკუმენტი", "ru": "Документ", "en": "Document"},
    "file": {"ka": "ფაილი", "ru": "Файл", "en": "File"},
    "sha": {"ka": "ანაბეჭდი (SHA-256)", "ru": "Отпечаток (SHA-256)", "en": "Fingerprint (SHA-256)"},
    "created": {"ka": "შექმნილია", "ru": "Создан", "en": "Created"},
    "completed": {"ka": "ხელმოწერილია", "ru": "Подписан", "en": "Signed"},
    "signer": {"ka": "ხელმომწერი", "ru": "Подписант", "en": "Signer"},
}
NOTE = {
    "ka": (
        "ორივე მხარემ დოკუმენტზე თანხმობა დაადასტურა თავისი Telegram ანგარიშით Bina.ai "
        "სერვისში (მარტივი ელექტრონული ხელმოწერა). SHA-256 ანაბეჭდით შეიძლება შემოწმდეს, "
        "რომ ფაილი ხელმოწერის შემდეგ არ შეცვლილა."
    ),
    "ru": (
        "Обе стороны подтвердили согласие с документом через свои аккаунты Telegram в сервисе "
        "Bina.ai (простая электронная подпись). По отпечатку SHA-256 можно проверить, что "
        "файл после подписи не меняли."
    ),
    "en": (
        "Both parties confirmed their consent to the document with their Telegram accounts "
        "in the Bina.ai service (simple electronic signature). The SHA-256 fingerprint shows "
        "whether the file was changed after signing."
    ),
}


def _when(moment: datetime) -> str:
    local = moment.astimezone(TBILISI)
    return f"{local:%d.%m.%Y %H:%M} (Tbilisi, UTC+4)"


def render_certificate(
    title: str,
    filename: str,
    sha256: str,
    created_at: datetime,
    completed_at: datetime | None,
    signers: list[Signer],
    second: str,
) -> bytes:
    """PDF-сертификат: документ, отпечаток и подписи сторон."""
    other = second if second in ("ru", "en") else "en"
    pdf = new_pdf()
    heading(pdf, TITLES["ka"], TITLES[other])

    def row(key: str, value: str) -> tuple[str, str]:
        return f"{LABELS[key]['ka']}: {value}", f"{LABELS[key][other]}: {value}"

    rows = [
        row("document", title),
        row("file", filename),
        row("sha", sha256),
        row("created", _when(created_at)),
    ]
    if completed_at is not None:
        rows.append(row("completed", _when(completed_at)))
    for number, signer in enumerate(signers, 1):
        value = f"{signer.name}, Telegram ID {signer.telegram_id}, {_when(signer.signed_at)}"
        rows.append(row("signer", f"{number}. {value}"))
    bilingual_table(pdf, rows)
    pdf.set_font(FONT, "", 9)
    small_print(pdf, NOTE["ka"], NOTE[other])
    return to_bytes(pdf)
