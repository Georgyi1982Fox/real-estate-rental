"""Общее для PDF: шрифт с грузинскими буквами и двуязычная таблица."""

from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

# DejaVu Sans: грузинский, кириллица, латиница (лицензия — fonts/LICENSE-DejaVu.txt)
FONTS = Path(__file__).parent / "fonts"
FONT = "DejaVu"


def new_pdf() -> FPDF:
    """A4 с подключённым шрифтом."""
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(12, 12, 12)
    pdf.add_font(FONT, "", str(FONTS / "DejaVuSans.ttf"))
    pdf.add_font(FONT, "B", str(FONTS / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    return pdf


def heading(pdf: FPDF, *lines: str) -> None:
    """Заголовок по центру: по строке на язык."""
    pdf.set_font(FONT, "B", 13)
    for line in lines:
        pdf.multi_cell(0, 7, line, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def bilingual_table(pdf: FPDF, rows: list[tuple[str, str]], font_size: float = 8.5) -> None:
    """Строки в две колонки: грузинский | второй язык."""
    pdf.set_font(FONT, "", font_size)
    with pdf.table(
        col_widths=(1, 1),
        first_row_as_headings=False,
        line_height=font_size * 0.55,
        padding=1.5,
        borders_layout="HORIZONTAL_LINES",
        headings_style=FontFace(emphasis="BOLD"),
        text_align="LEFT",
    ) as table:
        for left, right in rows:
            row = table.row()
            row.cell(left)
            row.cell(right)


def small_print(pdf: FPDF, *lines: str) -> None:
    """Мелкий текст внизу (дисклеймер)."""
    pdf.ln(4)
    pdf.set_font(FONT, "", 7)
    pdf.set_text_color(90, 90, 90)
    for line in lines:
        pdf.multi_cell(0, 3.8, line, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)


def to_bytes(pdf: FPDF) -> bytes:
    return bytes(pdf.output())
