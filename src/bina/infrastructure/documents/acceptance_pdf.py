"""PDF акта приёма-передачи квартиры (TASK-102)."""

from datetime import date

from fpdf import FPDF
from fpdf.fonts import FontFace

from bina.application.acceptance import (
    DISCLAIMER,
    TITLES,
    AcceptanceData,
    header_row,
    intro_rows,
    item_rows,
    meter_rows,
)
from bina.application.contract import signature_labels
from bina.infrastructure.documents.pdf import (
    FONT,
    bilingual_table,
    heading,
    new_pdf,
    signatures,
    small_print,
    to_bytes,
)


def _checklist(pdf: FPDF, second_language: str, rows: list[tuple[str, str, str]]) -> None:
    pdf.set_font(FONT, "", 8)
    with pdf.table(
        col_widths=(3, 1.6, 3),
        line_height=4.4,
        padding=1.2,
        borders_layout="HORIZONTAL_LINES",
        headings_style=FontFace(emphasis="BOLD"),
        text_align="LEFT",
    ) as table:
        header = table.row()
        for text in header_row(second_language):
            header.cell(text)
        for item, status, comment in rows:
            row = table.row()
            row.cell(item)
            row.cell(status)
            row.cell(comment)


def render_acceptance(
    data: AcceptanceData, second_language: str, today: date | None = None
) -> bytes:
    """Акт: заголовок, стороны и адрес, чек-лист, счётчики и ключи, подписи."""
    today = today or date.today()
    pdf = new_pdf()
    heading(pdf, TITLES["ka"], TITLES[second_language])
    pdf.set_font(FONT, "", 9)
    pdf.cell(0, 6, f"{today:%d.%m.%Y}", align="R", new_x="LMARGIN", new_y="NEXT")
    bilingual_table(pdf, intro_rows(data, second_language))
    pdf.ln(3)
    rows = item_rows(data, second_language)
    if rows:
        _checklist(pdf, second_language, rows)
        pdf.ln(3)
    meters = meter_rows(data, second_language)
    if meters:
        bilingual_table(pdf, meters)
    signatures(pdf, signature_labels(second_language), (data.landlord_name, data.tenant_name))
    small_print(pdf, DISCLAIMER["ka"], DISCLAIMER[second_language])
    return to_bytes(pdf)
