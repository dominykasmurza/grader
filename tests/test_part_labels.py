from openpyxl import Workbook

from grader.grading import (
    answer_key_part_labels,
    grade_detected_rows,
    load_answer_key,
    normalize_part,
    question_code_for,
)
from grader.part_detection import (
    infer_part_label_from_filename,
    infer_part_label_from_qr_text,
    resolve_part_label,
)


def _write_answer_key(path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Question", "PartLabel", "", "Answer1", "Answer2", "Answer3", "Answer4"])
    sheet.append([1, "Form-Alpha", "", "T", "F", "T", "F"])
    sheet.append([2, "Form-Alpha", "", "F", "F", "T", "T"])
    sheet.append([1, "Form-Beta", "", "T", "T", "F", "F"])
    workbook.save(path)


def test_load_generalized_answer_key(tmp_path):
    path = tmp_path / "answer_key.xlsx"
    _write_answer_key(path)

    answer_key = load_answer_key(path)

    assert answer_key_part_labels(answer_key) == ["Form-Alpha", "Form-Beta"]
    assert len(answer_key) == 3


def test_grade_by_part_label(tmp_path):
    path = tmp_path / "answer_key.xlsx"
    _write_answer_key(path)
    answer_key = load_answer_key(path)

    detected = [
        ["T", "F", "T", "F"],
        ["F", "F", "T", "T"],
    ]
    graded, metrics = grade_detected_rows(detected, answer_key, "Form-Alpha")

    assert graded[0]["part_label"] == "Form-Alpha"
    assert graded[0]["code"] == "Form-Alpha:01"
    assert metrics["correct"] == 8
    assert metrics["score"] == 2.0


def test_filename_matching_is_token_bounded():
    labels = ["A", "B"]
    assert infer_part_label_from_filename("BRA-123.pdf", labels)["part"] is None
    assert infer_part_label_from_filename("LTU-S1_A-1.pdf", labels)["part"] == "A"


def test_custom_filename_and_qr_matching():
    labels = ["Form-Alpha", "Form-Beta"]
    filename = infer_part_label_from_filename(
        "LTU-S1_Form-Alpha_scan.pdf",
        labels,
    )
    qr = infer_part_label_from_qr_text(
        "candidate=LTU-S1&part=Form-Beta",
        labels,
    )

    assert filename["part"] == "Form-Alpha"
    assert qr["part"] == "Form-Beta"


def test_filename_qr_conflict_is_not_silently_resolved():
    result = resolve_part_label(
        requested_part="auto",
        source_name="LTU-S1_Form-Alpha_scan.pdf",
        qr_text="candidate=LTU-S1&part=Form-Beta",
        part_labels=["Form-Alpha", "Form-Beta"],
    )

    assert result["part"] is None
    assert result["status"] == "filename_qr_part_conflict"


def test_explicit_label_must_exist_in_answer_key():
    result = resolve_part_label(
        requested_part="Unknown-Form",
        source_name="sheet.pdf",
        qr_text="",
        part_labels=["Form-Alpha"],
    )

    assert result["part"] is None
    assert result["status"] == "explicit_part_not_in_answer_key"


def test_legacy_aliases_and_codes_still_work():
    assert normalize_part("Part A") == "A"
    assert normalize_part("part b") == "B"
    assert question_code_for("A", 1) == "A01"
    assert question_code_for("Form-Alpha", 1) == "Form-Alpha:01"


def test_detailed_csv_repeats_part_label_for_every_question(tmp_path):
    import csv

    from grader.reporting import write_detailed_sheet_csv

    output = tmp_path / "sheet.csv"
    detected_rows = [["T", "F", "T", "F"], ["F", "T", "F", "T"]]
    graded_rows = [
        {
            "question": 1,
            "code": "Form-Alpha:01",
            "correct": ["T", "F", "T", "F"],
            "result": ["correct"] * 4,
            "correct_count": 4,
            "gradable_count": 4,
            "score": 1.0,
            "max_score": 1.0,
        }
    ]
    grade_metrics = {
        "correct": 4,
        "incorrect": 0,
        "missing": 0,
        "score": 1.0,
        "max_score": 1.0,
        "grading_status": "graded",
        "part_resolution_source": "filename",
        "part_resolution_status": "resolved_filename",
        "filename_part_matches": ["Form-Alpha"],
        "qr_part_matches": [],
    }

    write_detailed_sheet_csv(
        csv_path=output,
        source_name="candidate_Form-Alpha.pdf",
        page_number=1,
        detected_rows=detected_rows,
        metrics={"detected_T": 4, "detected_F": 4, "empty": 0, "ambiguous": 0},
        qr_info={"text": "", "status": "not_detected"},
        title_info={"text": "", "status": "disabled", "confidence": None},
        alignment_info={"marker_count": 4, "marker_names": [], "missing_marker_names": [], "mode": "test"},
        resolved_part="Form-Alpha",
        graded_rows=graded_rows,
        grade_metrics=grade_metrics,
        timestamp_text="",
    )

    with output.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    question_rows = [row for row in rows if row["Question"] != "TOTAL"]
    assert [row["PartLabel"] for row in question_rows] == ["Form-Alpha", "Form-Alpha"]
    assert all(row["GradingStatus"] == "graded" for row in question_rows)
