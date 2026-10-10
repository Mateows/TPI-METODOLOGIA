"""Genera informe-discovery.pdf desde informe-discovery.md (Etapa 2.4).

Uso (desde docs/discovery/):
    ..\\backend\\.venv\\Scripts\\python.exe make_pdf.py
Requiere: pip install reportlab markdown
Convierte Markdown -> HTML -> flowables ReportLab con estilos propios:
portada, encabezados con color, tablas anchas en apaisada con encabezado
repetido y zebra, pie con numeracion.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import markdown
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable,
                                PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

HERE = Path(__file__).resolve().parent
SRC = HERE / "informe-discovery.md"
DST = HERE / "informe-discovery.pdf"

ACCENT = colors.HexColor("#1F4E79")
LIGHT_LINE = colors.HexColor("#BDD7EE")
ZEBRA = colors.HexColor("#EAF2FA")
CODE_BG = colors.HexColor("#F2F2F2")
LINK = colors.HexColor("#0563C1")

ST = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=17,
                         leading=21, textColor=ACCENT, spaceBefore=14, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13,
                         leading=16, textColor=ACCENT, spaceBefore=12, spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=11,
                         leading=14, spaceBefore=8, spaceAfter=4),
    "p": ParagraphStyle("p", fontName="Helvetica", fontSize=9.5,
                        leading=13.5, alignment=TA_LEFT, spaceAfter=5),
    "li": ParagraphStyle("li", fontName="Helvetica", fontSize=9.5,
                         leading=13.5, leftIndent=14, bulletIndent=6, spaceAfter=3),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=7.5,
                           leading=9),
    "cellH": ParagraphStyle("cellH", fontName="Helvetica-Bold", fontSize=7.5,
                            leading=9, textColor=colors.white),
    "quote": ParagraphStyle("quote", fontName="Helvetica-Oblique", fontSize=9,
                            leading=12.5, leftIndent=12, textColor=colors.HexColor("#404040"),
                            spaceAfter=5),
    "cover_title": ParagraphStyle("ct", fontName="Helvetica-Bold", fontSize=24,
                                  leading=29, textColor=ACCENT, alignment=TA_CENTER,
                                  spaceAfter=6),
    "cover_sub": ParagraphStyle("cs", fontName="Helvetica", fontSize=12,
                                leading=16, alignment=TA_CENTER, spaceAfter=3),
}


def _break_urls(text: str) -> str:
    """Permite cortar URLs largas despues de cada barra (solo en celdas)."""
    return re.sub(r"(https?://\S+)",
                  lambda m: m.group(1).replace("/", "/<br/>"), text)


class MD2Story(HTMLParser):
    """Convierte el HTML del markdown en flowables ReportLab."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.story: list = []
        self._buf = ""
        self._tag: str | None = None
        self._lists: list[str] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell_head = False
        self._in_table = False
        self._drop_first_h1 = True

    # -- texto ---------------------------------------------------------
    def handle_data(self, data: str) -> None:
        if self._in_table and self._row is not None:
            self._buf += data
        elif self._tag in ("h1", "h2", "h3", "p", "li", "quote"):
            self._buf += data

    # -- estructura ----------------------------------------------------
    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in ("h1", "h2", "h3", "p", "li"):
            self._tag, self._buf = tag, ""
        elif tag == "blockquote":
            self._tag, self._buf = "quote", ""
        elif tag in ("ul", "ol"):
            self._lists.append(tag)
        elif tag == "table":
            self._in_table, self._table = True, []
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell_head = tag == "th"
            self._buf = ""
        elif tag == "br":
            self._buf += "<br/>"
        elif tag in ("strong", "b"):
            self._buf += "<b>"
        elif tag in ("em", "i"):
            self._buf += "</b>" if False else "<i>"
        elif tag == "code":
            self._buf += '<font face="Courier" size="8" backColor="#F2F2F2">'
        elif tag == "a":
            href = dict(attrs).get("href", "")
            self._buf += f'<a href="{href}" color="#0563C1">'

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1" and self._drop_first_h1:
            self._drop_first_h1 = False  # el titulo ya esta en portada
            self._tag, self._buf = None, ""
        elif tag in ("h1", "h2", "h3", "p", "quote"):
            text = self._buf.strip()
            if text:
                self.story.append(Paragraph(text, ST[tag]))
            self._tag, self._buf = None, ""
        elif tag == "li":
            bullet = "\u2022" if (self._lists and self._lists[-1] == "ul") else "1."
            text = self._buf.strip()
            if text:
                self.story.append(Paragraph(f"{bullet}&nbsp;&nbsp;{text}", ST["li"],
                                            bulletText=""))
            self._tag, self._buf = None, ""
        elif tag in ("ul", "ol"):
            if self._lists:
                self._lists.pop()
            self.story.append(Spacer(1, 2))
        elif tag == "code":
            self._buf += "</font>"
        elif tag == "a":
            self._buf += "</a>"
        elif tag in ("em", "i"):
            self._buf += "</i>"
        elif tag in ("strong", "b"):
            self._buf += "</b>"
        elif tag in ("td", "th"):
            if self._row is not None:
                cell = _break_urls(self._buf.strip())
                self._row.append(("H:" if self._cell_head else "") + cell)
            self._buf = ""
        elif tag == "tr":
            if self._table is not None and self._row is not None:
                self._table.append(self._row)
            self._row = None
        elif tag == "table":
            self._in_table = False
            if self._table:
                self.story.append(("TABLE", self._table))
            self._table = None
        elif tag == "hr":
            self.story.append(HRFlowable(width="100%", thickness=0.7,
                                         color=LIGHT_LINE, spaceAfter=6))


def _table_flowable(rows: list[list[str]], landscape_w: float) -> Table:
    ncols = max(len(r) for r in rows)
    padded = [r + [""] * (ncols - len(r)) for r in rows]
    body, head = [], []
    for i, row in enumerate(padded):
        cells = []
        for cell in row:
            is_h = cell.startswith("H:")
            txt = cell[2:] if is_h else cell
            cells.append(Paragraph(txt or "-", ST["cellH"] if is_h else ST["cell"]))
            if is_h:
                head.append(True)
        body.append(cells)
    has_header = any(head)
    widths = [landscape_w / ncols] * ncols
    t = Table(body, colWidths=widths, repeatRows=1 if has_header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 3),
             ("RIGHTPADDING", (0, 0), (-1, -1), 3),
             ("TOPPADDING", (0, 0), (-1, -1), 2),
             ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if has_header:
        style += [("BACKGROUND", (0, 0), (-1, 0), ACCENT),
                  ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
        for i in range(1, len(body), 2):
            style.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    t.setStyle(TableStyle(style))
    return t


def _footer(canvas, doc) -> None:  # noqa: ANN001, ANN202
    canvas.saveState()
    canvas.setFont("Helvetica-Oblique", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(doc.pagesize[0] / 2, 12 * mm / 2.54,
                             f"TPI Metodologia - Informe de Discovery - pag. {doc.page}")
    canvas.restoreState()


def main() -> None:
    text = SRC.read_text(encoding="utf-8")
    # Limpieza minima fiel: Helvetica/ReportLab es cp1252 (-> y − no existen).
    text = text.replace("⚠️", "[!]").replace("⚠", "[!]").replace("️", "")
    text = text.replace("→", "->").replace("−", "-")
    html = markdown.markdown(text, extensions=["tables"])

    parser = MD2Story()
    parser.feed(html)
    items = parser.story

    story: list = [
        Spacer(1, 55),
        Paragraph("Informe de Discovery", ST["cover_title"]),
        Paragraph("TPI Metodología — SaaS odontológico (Argentina / LATAM)", ST["cover_sub"]),
        Spacer(1, 6),
        Paragraph("Metodología I — Trabajo de Integración · Etapa 2", ST["cover_sub"]),
        Paragraph("Derivado de discovery/discovery.md + research Etapa 2.1 · 2026-10-09", ST["cover_sub"]),
        PageBreak(),
    ]
    pw, ph = A4
    for it in items:
        if isinstance(it, tuple) and it[0] == "TABLE":
            # Documento 100% retrato: las celdas ya vienen condensadas (<=120)
            # y el encabezado se repite en cada pagina. Sin cambios de
            # plantilla -> sin paginas en blanco.
            story.append(_table_flowable(it[1], pw - 40))
            story.append(Spacer(1, 6))
        else:
            story.append(it)

    doc = BaseDocTemplate(str(DST), pagesize=A4,
                          leftMargin=20, rightMargin=20, topMargin=18, bottomMargin=18,
                          showBoundary=0)
    portrait = Frame(doc.leftMargin, doc.bottomMargin,
                     doc.width, doc.height, id="portrait")
    doc.addPageTemplates([
        PageTemplate(id="portrait", frames=[portrait], onPage=_footer),
    ])
    doc.build(story)
    print(f"OK: {DST} ({DST.stat().st_size} bytes)")


if __name__ == "__main__":
    assert SRC.exists(), f"falta {SRC}"
    main()
