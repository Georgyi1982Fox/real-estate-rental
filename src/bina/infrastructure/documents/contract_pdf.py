"""PDF двуязычного договора аренды (TASK-101)."""

from datetime import date

from bina.application.contract import (
    DISCLAIMER,
    TITLES,
    ContractData,
    contract_clauses,
    signature_labels,
)
from bina.infrastructure.documents.pdf import (
    FONT,
    bilingual_table,
    heading,
    new_pdf,
    signatures,
    small_print,
    to_bytes,
)


def render_contract(data: ContractData, second_language: str, today: date | None = None) -> bytes:
    """Договор: заголовок на двух языках, пункты в две колонки, подписи, дисклеймер."""
    today = today or date.today()
    pdf = new_pdf()
    heading(pdf, TITLES["ka"], TITLES[second_language])
    pdf.set_font(FONT, "", 9)
    pdf.cell(0, 6, f"{today:%d.%m.%Y}", align="R", new_x="LMARGIN", new_y="NEXT")
    bilingual_table(pdf, contract_clauses(data, second_language))

    signatures(pdf, signature_labels(second_language), (data.landlord_name, data.tenant_name))
    small_print(pdf, DISCLAIMER["ka"], DISCLAIMER[second_language])
    return to_bytes(pdf)
