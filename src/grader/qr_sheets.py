"""Generate QR-encoded answer sheets from a CSV file.

Each non-empty CSV row becomes one page in a single PDF. The QR code is
placed in the reserved area at the top center of the standard answer sheet.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .config import (
    MM,
    MARGIN_Y_PT,
    PDF_H_PT,
    PDF_W_PT,
    QR_RESERVED_H_PT,
    QR_RESERVED_W_PT,
)
from .templates import draw_sheet_page


@dataclass(frozen=True)
class QRSheetRecord:
    """One answer-sheet page requested by a CSV row."""

    qr_text: str
    label: str | None = None
    sheet_label: str | None = None


def _normalize_header(value: str) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _resolve_column(
    fieldnames: list[str],
    requested: str | None,
    candidates: Iterable[str],
    required: bool,
) -> str | None:
    normalized = {_normalize_header(name): name for name in fieldnames}

    if requested:
        key = _normalize_header(requested)
        if key not in normalized:
            raise ValueError(
                f"CSV column {requested!r} was not found. "
                f"Available columns: {', '.join(fieldnames)}"
            )
        return normalized[key]

    for candidate in candidates:
        key = _normalize_header(candidate)
        if key in normalized:
            return normalized[key]

    if required:
        raise ValueError(
            "Could not identify the QR-text column. Use --text-column. "
            f"Available columns: {', '.join(fieldnames)}"
        )

    return None


def read_qr_sheet_csv(
    csv_path: str | Path,
    text_column: str | None = None,
    label_column: str | None = None,
    sheet_label_column: str | None = None,
    default_sheet_label: str | None = None,
    encoding: str = "utf-8-sig",
) -> list[QRSheetRecord]:
    """Read QR payloads and optional page labels from a CSV file."""

    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    records: list[QRSheetRecord] = []

    with path.open("r", newline="", encoding=encoding) as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("The CSV file has no header row.")

        fields = list(reader.fieldnames)

        text_col = _resolve_column(
            fields,
            text_column,
            ("qr_text", "qr", "code", "text", "payload", "student_code"),
            required=True,
        )
        label_col = _resolve_column(
            fields,
            label_column,
            ("label", "display_text", "student", "student_code"),
            required=False,
        )
        sheet_label_col = _resolve_column(
            fields,
            sheet_label_column,
            (
                "sheet_label",
                "header",
                "header_text",
                "title",
                "sheet_title",
                "template_label",
            ),
            required=False,
        )

        normalized_default_sheet_label = (
            str(default_sheet_label).strip() if default_sheet_label else None
        )

        for row in reader:
            qr_text = str(row.get(text_col, "") or "").strip()
            if not qr_text:
                continue

            raw_label = row.get(label_col, "") if label_col else ""
            label = str(raw_label or "").strip() or None

            raw_sheet_label = (
                row.get(sheet_label_col, "") if sheet_label_col else ""
            )
            sheet_label = (
                str(raw_sheet_label or "").strip()
                or normalized_default_sheet_label
                or None
            )

            records.append(
                QRSheetRecord(
                    qr_text=qr_text,
                    label=label,
                    sheet_label=sheet_label,
                )
            )

    if not records:
        raise ValueError("No non-empty QR payloads were found in the CSV file.")

    return records


def draw_qr_code(
    pdf_canvas: canvas.Canvas,
    text: str,
    size_pt: float,
    x_pt: float,
    y_pt: float,
    error_correction: str = "M",
) -> None:
    """Draw a vector QR code at the requested PDF coordinates."""

    level = str(error_correction).upper()
    if level not in {"L", "M", "Q", "H"}:
        raise ValueError(
            "QR error correction must be one of L, M, Q, or H."
        )

    widget = qr.QrCodeWidget(text, barLevel=level)
    x0, y0, x1, y1 = widget.getBounds()
    width = x1 - x0
    height = y1 - y0

    drawing = Drawing(
        size_pt,
        size_pt,
        transform=[
            size_pt / width,
            0,
            0,
            size_pt / height,
            0,
            0,
        ],
    )
    drawing.add(widget)
    renderPDF.draw(drawing, pdf_canvas, x_pt, y_pt)


def generate_qr_answer_sheets(
    records: Iterable[QRSheetRecord],
    output_pdf: str | Path,
    logo_path: str | None = None,
    qr_size_mm: float = 29.0,
    error_correction: str = "M",
    print_text: bool = False,
    qr_label_font_size_pt: float = 9.0,
) -> int:
    """Generate one multipage PDF containing one sheet per record."""

    output_path = Path(output_pdf)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    qr_size_pt = float(qr_size_mm) * MM
    max_size_pt = min(QR_RESERVED_W_PT, QR_RESERVED_H_PT)

    if qr_size_pt <= 0 or qr_size_pt > max_size_pt:
        raise ValueError(
            "QR size must be greater than 0 and at most "
            f"{max_size_pt / MM:.1f} mm."
        )

    if qr_label_font_size_pt <= 0:
        raise ValueError("QR-label font size must be greater than 0.")

    items = list(records)
    if not items:
        raise ValueError("At least one QR sheet record is required.")

    pdf = canvas.Canvas(str(output_path), pagesize=A4)

    qr_x = (PDF_W_PT - qr_size_pt) / 2
    qr_y = (
        PDF_H_PT
        - MARGIN_Y_PT
        - (QR_RESERVED_H_PT + qr_size_pt) / 2
    )

    for record in items:
        draw_sheet_page(
            pdf,
            fill_answers=False,
            label_text=record.sheet_label,
            logo_path=logo_path,
        )

        draw_qr_code(
            pdf,
            text=record.qr_text,
            size_pt=qr_size_pt,
            x_pt=qr_x,
            y_pt=qr_y,
            error_correction=error_correction,
        )

        if print_text:
            visible_text = record.label or record.qr_text
            max_chars = 80
            if len(visible_text) > max_chars:
                visible_text = visible_text[: max_chars - 3] + "..."

            pdf.setFillColorRGB(0, 0, 0)
            pdf.setFont("Helvetica", qr_label_font_size_pt)
            pdf.drawCentredString(
                PDF_W_PT / 2,
                qr_y - 4.0 * MM,
                visible_text,
            )

        pdf.showPage()

    pdf.save()
    return len(items)


def generate_qr_answer_sheets_from_csv(
    csv_path: str | Path,
    output_pdf: str | Path,
    text_column: str | None = None,
    label_column: str | None = None,
    sheet_label_column: str | None = None,
    default_sheet_label: str | None = None,
    logo_path: str | None = None,
    qr_size_mm: float = 29.0,
    error_correction: str = "M",
    print_text: bool = False,
    qr_label_font_size_pt: float = 9.0,
) -> int:
    """Read a CSV and generate its QR-encoded answer-sheet PDF."""

    records = read_qr_sheet_csv(
        csv_path=csv_path,
        text_column=text_column,
        label_column=label_column,
        sheet_label_column=sheet_label_column,
        default_sheet_label=default_sheet_label,
    )

    return generate_qr_answer_sheets(
        records=records,
        output_pdf=output_pdf,
        logo_path=logo_path,
        qr_size_mm=qr_size_mm,
        error_correction=error_correction,
        print_text=print_text,
        qr_label_font_size_pt=qr_label_font_size_pt,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a multipage PDF of QR-encoded grader answer "
            "sheets from a CSV file."
        )
    )

    parser.add_argument(
        "csv_path",
        help="Input CSV containing one QR payload per row.",
    )
    parser.add_argument(
        "output_pdf",
        nargs="?",
        default="qr_answer_sheets.pdf",
        help="Output multipage PDF. Default: qr_answer_sheets.pdf",
    )
    parser.add_argument(
        "--text-column",
        default=None,
        help=(
            "Column containing the QR payload. Common names such as "
            "qr_text, qr, code, text, payload, and student_code are "
            "detected automatically."
        ),
    )
    parser.add_argument(
        "--label-column",
        default=None,
        help="Optional column used as readable text below the QR code.",
    )
    parser.add_argument(
        "--sheet-label-column",
        default=None,
        help=(
            "Optional CSV column containing customizable text printed "
            "at the top left of each answer sheet."
        ),
    )
    parser.add_argument(
        "--default-sheet-label",
        default=None,
        help=(
            "Default top-left label used when a row has no sheet-label "
            "value."
        ),
    )
    parser.add_argument(
        "--logo-path",
        default=None,
        help="Optional logo image placed near the top-right marker.",
    )
    parser.add_argument(
        "--qr-size-mm",
        type=float,
        default=29.0,
        help=(
            "QR-code width and height in millimetres. "
            "Maximum: 30. Default: 29."
        ),
    )
    parser.add_argument(
        "--qr-label-font-size",
        type=float,
        default=9.0,
        help=(
            "Font size in points for readable text below the QR code. "
            "Default: 9."
        ),
    )
    parser.add_argument(
        "--error-correction",
        choices=["L", "M", "Q", "H"],
        default="M",
        help="QR error-correction level. Default: M.",
    )
    parser.add_argument(
        "--print-text",
        action="store_true",
        help="Print the label or QR payload below the code.",
    )

    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    count = generate_qr_answer_sheets_from_csv(
        csv_path=args.csv_path,
        output_pdf=args.output_pdf,
        text_column=args.text_column,
        label_column=args.label_column,
        sheet_label_column=args.sheet_label_column,
        default_sheet_label=args.default_sheet_label,
        logo_path=args.logo_path,
        qr_size_mm=args.qr_size_mm,
        error_correction=args.error_correction,
        print_text=args.print_text,
        qr_label_font_size_pt=args.qr_label_font_size,
    )

    print(f"Created {args.output_pdf} with {count} pages.")


if __name__ == "__main__":
    main()
