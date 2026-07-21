"""Per-sheet and aggregate CSV reporting."""

import csv
import os

from .config import *
from .grading import question_code_for
from .part_detection import (
    determine_part_resolution_source,
    infer_part_from_filename_marker,
)


def write_detailed_sheet_csv(
    csv_path,
    source_name,
    page_number,
    detected_rows,
    metrics,
    qr_info,
    printed_part_info,
    alignment_info,
    resolved_part,
    graded_rows,
    grade_metrics,
    timestamp_text,
    grader_text=GRADER_HEADER_TEXT,
):
    """Write one detailed CSV for one detected sheet/page."""
    fieldnames = [
        "SourcePDF",
        "Page",
        "Grader",
        "GeneratedAt",
        "Part",
        "QRText",
        "QRStatus",
        "PrintoutPart",
        "PrintoutPartStatus",
        "PrintoutPartConfidence",
        "ArUcoMarkersDetected",
        "ArUcoMarkerNames",
        "ArUcoMissingMarkers",
        "AlignmentMode",
        "Question",
        "Code",
        "Detected1",
        "Detected2",
        "Detected3",
        "Detected4",
        "Correct1",
        "Correct2",
        "Correct3",
        "Correct4",
        "Result1",
        "Result2",
        "Result3",
        "Result4",
        "CorrectCount",
        "GradableCount",
        "QuestionScore",
        "QuestionMaxScore",
        "DetectedT",
        "DetectedF",
        "Empty",
        "Ambiguous",
        "TotalCorrect",
        "TotalIncorrect",
        "TotalMissing",
        "TotalScore",
        "TotalMaxScore",
    ]

    graded_by_q = {row["question"]: row for row in graded_rows}
    common = {
        "SourcePDF": os.path.basename(source_name) if source_name else "",
        "Page": page_number,
        "Grader": grader_text,
        "GeneratedAt": timestamp_text,
        "Part": resolved_part or "",
        "QRText": qr_info.get("text", ""),
        "QRStatus": qr_info.get("status", ""),
        "PrintoutPart": printed_part_info.get("part") or "",
        "PrintoutPartStatus": printed_part_info.get("status", ""),
        "PrintoutPartConfidence": printed_part_info.get("confidence", 0.0),
        "ArUcoMarkersDetected": alignment_info.get("marker_count", 0),
        "ArUcoMarkerNames": ";".join(alignment_info.get("marker_names", [])),
        "ArUcoMissingMarkers": ";".join(alignment_info.get("missing_marker_names", [])),
        "AlignmentMode": alignment_info.get("mode", ""),
    }

    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for q_idx, detected in enumerate(detected_rows, start=1):
            graded = graded_by_q.get(q_idx)
            row = dict(common)
            row.update({
                "Question": q_idx,
                "Code": graded["code"] if graded else question_code_for(resolved_part, q_idx),
            })

            for i in range(STATEMENTS_PER_QUESTION):
                row[f"Detected{i + 1}"] = detected[i] if i < len(detected) else ""

            if graded:
                for i in range(STATEMENTS_PER_QUESTION):
                    row[f"Correct{i + 1}"] = graded["correct"][i]
                    row[f"Result{i + 1}"] = graded["result"][i]
                row["CorrectCount"] = graded.get("correct_count", "")
                row["GradableCount"] = graded.get("gradable_count", "")
                row["QuestionScore"] = graded.get("score", "")
                row["QuestionMaxScore"] = graded.get("max_score", "")

            writer.writerow(row)

        summary = dict(common)
        summary.update({
            "Question": "TOTAL",
            "DetectedT": metrics.get("detected_T", 0),
            "DetectedF": metrics.get("detected_F", 0),
            "Empty": metrics.get("empty", 0),
            "Ambiguous": metrics.get("ambiguous", 0),
            "TotalCorrect": grade_metrics.get("correct", ""),
            "TotalIncorrect": grade_metrics.get("incorrect", ""),
            "TotalMissing": grade_metrics.get("missing", ""),
            "TotalScore": grade_metrics.get("score", ""),
            "TotalMaxScore": grade_metrics.get("max_score", ""),
        })
        writer.writerow(summary)


def _safe_percent(numerator, denominator):
    try:
        numerator = float(numerator)
        denominator = float(denominator)
    except (TypeError, ValueError):
        return ""
    if denominator <= 0:
        return ""
    return round(100.0 * numerator / denominator, 4)


def _result_entry_to_metrics_row(entry, output_root):
    """Convert one processed page result into one all-files metrics row."""
    source_pdf = entry.get("source_pdf", "")
    relative_source = entry.get("relative_source_path") or os.path.basename(source_pdf)
    status = entry.get("status", "ok")
    error = entry.get("error", "")
    page = entry.get("page", "")
    filename_info = infer_part_from_filename_marker(source_pdf)

    row = {field: "" for field in ALL_FILES_METRICS_FIELDS}
    row.update({
        "SourceRelativePath": relative_source,
        "SourcePDF": os.path.basename(source_pdf) if source_pdf else "",
        "Page": page,
        "Status": status,
        "Error": error,
        "FilenamePart": filename_info.get("part") or "",
        "FilenamePartStatus": filename_info.get("status", ""),
        "DetectedFile": entry.get("detected_file") or entry.get("detected_png", ""),
        "DetailedCSV": entry.get("detailed_csv", ""),
    })

    detected_png = entry.get("detected_file") or entry.get("detected_png", "")
    if detected_png:
        try:
            row["OutputRelativeFolder"] = os.path.relpath(
                os.path.dirname(detected_png), output_root
            )
        except ValueError:
            row["OutputRelativeFolder"] = os.path.dirname(detected_png)

    if detected_png and os.path.exists(detected_png):
        size_bytes = os.path.getsize(detected_png)
        row["DetectedFileSizeBytes"] = size_bytes
        row["DetectedFileSizeMiB"] = round(size_bytes / (1024 * 1024), 4)

    if status != "ok" or not entry.get("result"):
        return row

    (
        detected_rows,
        metrics,
        qr_info,
        graded_rows,
        grade_metrics,
        resolved_part,
        printed_part_info,
        alignment_info,
    ) = entry["result"]

    requested_part = entry.get("requested_part", "auto")
    row["PartResolutionSource"] = determine_part_resolution_source(
        requested_part,
        filename_info,
        printed_part_info,
        qr_info,
        resolved_part,
    )
    row["ResolvedPart"] = resolved_part or ""
    row["QRText"] = qr_info.get("text", "")
    row["QRStatus"] = qr_info.get("status", "")
    row["PrintoutPart"] = printed_part_info.get("part") or ""
    row["PrintoutPartStatus"] = printed_part_info.get("status", "")
    row["PrintoutPartConfidence"] = printed_part_info.get("confidence", 0.0)
    row["ArUcoMarkersDetected"] = alignment_info.get("marker_count", 0)
    row["ArUcoMarkerNames"] = ";".join(alignment_info.get("marker_names", []))
    row["ArUcoMissingMarkers"] = ";".join(alignment_info.get("missing_marker_names", []))
    row["AlignmentMode"] = alignment_info.get("mode", "")

    total_cells = metrics.get("total_cells", 0)
    detected_t = metrics.get("detected_T", 0)
    detected_f = metrics.get("detected_F", 0)
    empty_including_ambiguous = metrics.get("empty", 0)
    ambiguous = metrics.get("ambiguous", 0)
    strict_empty = max(0, empty_including_ambiguous - ambiguous)

    row.update({
        "TotalCells": total_cells,
        "DetectedTrue": detected_t,
        "DetectedFalse": detected_f,
        "DetectedResponses": detected_t + detected_f,
        "EmptyIncludingAmbiguous": empty_including_ambiguous,
        "StrictEmpty": strict_empty,
        "Ambiguous": ambiguous,
        "GradableCells": grade_metrics.get("gradable_cells", 0),
        "Correct": grade_metrics.get("correct", 0),
        "Incorrect": grade_metrics.get("incorrect", 0),
        "Missing": grade_metrics.get("missing", 0),
        "LinearCorrectCells": grade_metrics.get("linear_correct_cells", 0),
        "QuestionsScored": grade_metrics.get("question_count", 0),
        "Score": round(float(grade_metrics.get("score", 0.0) or 0.0), 6),
        "MaxScore": round(float(grade_metrics.get("max_score", 0.0) or 0.0), 6),
    })
    row["AccuracyPercent"] = _safe_percent(
        row["Correct"], row["GradableCells"]
    )
    row["ScorePercent"] = _safe_percent(row["Score"], row["MaxScore"])
    return row


def write_all_files_metrics_csv(csv_path, result_entries, output_root):
    """Write one metrics row per processed sheet/page and a final TOTAL row."""
    rows = [
        _result_entry_to_metrics_row(entry, output_root)
        for entry in result_entries
    ]

    numeric_sum_fields = [
        "TotalCells",
        "DetectedTrue",
        "DetectedFalse",
        "DetectedResponses",
        "EmptyIncludingAmbiguous",
        "StrictEmpty",
        "Ambiguous",
        "GradableCells",
        "Correct",
        "Incorrect",
        "Missing",
        "LinearCorrectCells",
        "QuestionsScored",
        "Score",
        "MaxScore",
        "DetectedFileSizeBytes",
        "DetectedFileSizeMiB",
    ]

    total = {field: "" for field in ALL_FILES_METRICS_FIELDS}
    ok_count = sum(1 for row in rows if row.get("Status") == "ok")
    failed_count = sum(1 for row in rows if row.get("Status") != "ok")
    total.update({
        "SourceRelativePath": "TOTAL",
        "SourcePDF": "TOTAL",
        "Status": "summary",
        "Error": f"{ok_count} successful sheet(s); {failed_count} failed sheet(s)",
    })
    for field in numeric_sum_fields:
        total[field] = sum(
            float(row.get(field, 0) or 0)
            for row in rows
            if row.get("Status") == "ok"
        )

    # Keep totals compact and avoid floating-point artifacts such as 40.5999999.
    for field in numeric_sum_fields:
        value = round(float(total[field]), 6)
        total[field] = int(value) if value.is_integer() else value

    total["AccuracyPercent"] = _safe_percent(
        total["Correct"], total["GradableCells"]
    )
    total["ScorePercent"] = _safe_percent(total["Score"], total["MaxScore"])
    rows.append(total)

    os.makedirs(os.path.dirname(os.path.abspath(csv_path)), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_FILES_METRICS_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"All-files grader metrics saved: {csv_path}")
    return rows
