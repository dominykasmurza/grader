import csv
from pathlib import Path

from pypdf import PdfReader

from grader.qr_sheets import (
    generate_qr_answer_sheets_from_csv,
    read_qr_sheet_csv,
)


def test_read_qr_csv(tmp_path):
    source = tmp_path / "codes.csv"
    source.write_text(
        "qr_text,part,label\n"
        "STUDENT-1-A,A,Student 1\n"
        "STUDENT-1-B,B,Student 1\n",
        encoding="utf-8",
    )

    records = read_qr_sheet_csv(source)
    assert len(records) == 2
    assert records[0].qr_text == "STUDENT-1-A"
    assert records[1].part == "B"


def test_generate_multipage_qr_pdf(tmp_path):
    source = tmp_path / "codes.csv"
    output = tmp_path / "sheets.pdf"
    source.write_text(
        "qr_text,part\nCODE-A,A\nCODE-B,B\n",
        encoding="utf-8",
    )

    count = generate_qr_answer_sheets_from_csv(source, output)
    assert count == 2
    assert output.exists()
    assert len(PdfReader(str(output)).pages) == 2
