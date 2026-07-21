from pypdf import PdfReader

from grader.qr_sheets import (
    generate_qr_answer_sheets_from_csv,
    read_qr_sheet_csv,
)


def test_read_qr_csv_with_custom_labels(tmp_path):
    source = tmp_path / "codes.csv"
    source.write_text(
        "qr_text,label,sheet_label\n"
        "STUDENT-1-A,Student 1,Examination A\n"
        "STUDENT-1-B,Student 1,Examination B\n",
        encoding="utf-8",
    )

    records = read_qr_sheet_csv(source)

    assert len(records) == 2
    assert records[0].qr_text == "STUDENT-1-A"
    assert records[0].label == "Student 1"
    assert records[1].sheet_label == "Examination B"


def test_default_sheet_label(tmp_path):
    source = tmp_path / "codes.csv"
    source.write_text(
        "qr_text,label\n"
        "CODE-A,Student A\n",
        encoding="utf-8",
    )

    records = read_qr_sheet_csv(
        source,
        default_sheet_label="Biology Examination",
    )

    assert records[0].sheet_label == "Biology Examination"


def test_generate_multipage_qr_pdf(tmp_path):
    source = tmp_path / "codes.csv"
    output = tmp_path / "sheets.pdf"

    source.write_text(
        "qr_text,sheet_label\n"
        "CODE-A,Examination A\n"
        "CODE-B,Examination B\n",
        encoding="utf-8",
    )

    count = generate_qr_answer_sheets_from_csv(source, output)

    assert count == 2
    assert output.exists()
    assert len(PdfReader(str(output)).pages) == 2
