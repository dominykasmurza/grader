#!/usr/bin/env bash
set -Eeuo pipefail

# Grader full demonstration
# Run from an active Python/Conda environment:
#   bash run_all_examples.sh
# or:
#   bash run_all_examples.sh /path/to/grader

ROOT="${1:-$HOME/grader}"
cd "$ROOT"

if [[ ! -f "pyproject.toml" || ! -d "src/grader" || ! -d "examples" ]]; then
  echo "ERROR: $ROOT does not look like the grader repository root." >&2
  exit 1
fi

echo
echo "============================================================"
echo "1. Install, compile, test, and inspect the command-line tools"
echo "============================================================"

python -m pip install -e ".[test]"
python -m compileall -q src
pytest -q

grader --help >/dev/null
grader-qr --help >/dev/null
python -m grader --help >/dev/null

if ! command -v pdftoppm >/dev/null 2>&1; then
  echo
  echo "ERROR: Poppler is required but pdftoppm was not found."
  echo "On macOS: brew install poppler"
  exit 1
fi

DEMO="$ROOT/demo_output"
rm -rf "$DEMO"
mkdir -p \
  "$DEMO/input" \
  "$DEMO/templates" \
  "$DEMO/qr" \
  "$DEMO/detection_only" \
  "$DEMO/bulk_default" \
  "$DEMO/explicit_custom_score" \
  "$DEMO/qr_detected" \
  "$DEMO/title_ocr"

echo
echo "============================================================"
echo "2. Prepare a demonstration answer key"
echo "============================================================"

# Make a copy compatible with both:
# - legacy A01/B01 question codes in column A; and
# - generalized PartLabel values in column B.
python - <<'PY'
from pathlib import Path
import re
from openpyxl import load_workbook

source = Path("examples/AnswerKey.xlsx")
target = Path("demo_output/input/AnswerKey_demo.xlsx")

if not source.exists():
    raise FileNotFoundError(source)

wb = load_workbook(source)
ws = wb.active

def norm(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").strip().lower())

header_row = None
for r in range(1, min(ws.max_row, 30) + 1):
    headers = [norm(ws.cell(r, c).value) for c in range(1, 8)]
    if any("question" in h for h in headers):
        header_row = r
        break

if header_row is None:
    header_row = 1

headers = {
    c: norm(ws.cell(header_row, c).value)
    for c in range(1, min(ws.max_column, 12) + 1)
}

part_col = next(
    (
        c for c, h in headers.items()
        if h in {"part", "partlabel", "exampart", "form", "formlabel"}
    ),
    None,
)
topic_col = next(
    (c for c, h in headers.items() if h in {"topic", "subject", "category"}),
    None,
)

# The repository example historically used:
# A = question code, B = topic, C = part.
if part_col is None and ws.max_column >= 3:
    values = [
        str(ws.cell(r, 3).value or "").strip()
        for r in range(header_row + 1, min(ws.max_row, header_row + 20) + 1)
    ]
    if any(v.upper() in {"A", "B"} for v in values):
        part_col = 3

if topic_col is None and ws.max_column >= 2 and part_col != 2:
    topic_col = 2

for r in range(header_row + 1, ws.max_row + 1):
    raw_question = ws.cell(r, 1).value
    if raw_question is None or str(raw_question).strip() == "":
        continue

    question_text = str(raw_question).strip()
    part = (
        str(ws.cell(r, part_col).value or "").strip()
        if part_col is not None
        else ""
    )

    code_match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*?)(\d{1,3})", question_text)
    if code_match:
        code_prefix = code_match.group(1)
        number = int(code_match.group(2))
        if not part:
            part = code_prefix
        # Preserve conventional A01/B01 codes for the included scans.
        if part.upper() in {"A", "B"}:
            question_text = f"{part.upper()}{number:02d}"
    elif re.fullmatch(r"\d+", question_text) and part:
        number = int(question_text)
        if part.upper() in {"A", "B"}:
            question_text = f"{part.upper()}{number:02d}"

    topic = (
        ws.cell(r, topic_col).value
        if topic_col is not None
        else None
    )

    ws.cell(r, 1).value = question_text
    ws.cell(r, 2).value = part
    ws.cell(r, 3).value = topic

ws.cell(header_row, 1).value = "Question"
ws.cell(header_row, 2).value = "PartLabel"
ws.cell(header_row, 3).value = "Topic"

target.parent.mkdir(parents=True, exist_ok=True)
wb.save(target)
print(f"Created {target}")
PY

python - <<'PY'
from openpyxl import load_workbook

ws = load_workbook(
    "demo_output/input/AnswerKey_demo.xlsx",
    data_only=True,
).active

print("First answer-key rows:")
for row in ws.iter_rows(min_row=1, max_row=min(6, ws.max_row), values_only=True):
    print(row[:7])
PY

echo
echo "============================================================"
echo "3. Generate ordinary answer-sheet templates"
echo "============================================================"

EMPTY_TEMPLATE="$(python -c 'from grader.config import EMPTY_TEMPLATE_PDF; print(EMPTY_TEMPLATE_PDF)')"
MOCK_TEMPLATE="$(python -c 'from grader.config import MOCK_PDF; print(MOCK_PDF)')"

# Blank template: no logo, QR, or title.
grader --template-only --skip-mock-generation
cp "$EMPTY_TEMPLATE" "$DEMO/templates/template_blank.pdf"

# Custom title, logo, and synthetic filled example.
grader --template-only \
  --template-label "Grader demonstration" \
  --logo-path "examples/grader.png"

cp "$EMPTY_TEMPLATE" "$DEMO/templates/template_custom_label_and_logo.pdf"
cp "$MOCK_TEMPLATE" "$DEMO/templates/template_filled_synthetic.pdf"

rm -f "$EMPTY_TEMPLATE" "$MOCK_TEMPLATE"

echo
echo "============================================================"
echo "4. Generate a multipage QR-encoded answer-sheet PDF"
echo "============================================================"

# Recreate a clean CSV with real line breaks rather than relying on editor export.
cat > "$DEMO/input/qr_sheets_demo.csv" <<'CSV'
qr_text,label,sheet_label
candidate=ABC-S1&part=A,ABC-S1 A,Theory examination - Part A
candidate=ABC-S1&part=B,ABC-S1 B,Theory examination - Part B
candidate=ABC-S2&part=A,ABC-S2 A,
candidate=ABC-S2&part=B,ABC-S2 B,
CSV

grader-qr \
  "$DEMO/input/qr_sheets_demo.csv" \
  "$DEMO/qr/qr_answer_sheets.pdf" \
  --text-column qr_text \
  --label-column label \
  --sheet-label-column sheet_label \
  --default-sheet-label "Default biology examination" \
  --logo-path "examples/grader.png" \
  --qr-size-mm 29 \
  --qr-label-font-size 9 \
  --error-correction M \
  --print-text

echo
echo "============================================================"
echo "5. Detection-only processing of one real scan"
echo "============================================================"

ONE_SCAN="$(
  find "examples/scanned_sheets" -type f -iname '*.pdf' -print | sort | sed -n '1p'
)"

if [[ -z "$ONE_SCAN" ]]; then
  echo "ERROR: No PDFs found under examples/scanned_sheets." >&2
  exit 1
fi

grader "$ONE_SCAN" \
  --output-folder "$DEMO/detection_only" \
  --skip-template-generation \
  --disable-qr-reader \
  --timestamp \
  --grader-label "Grader demonstration - detection only" \
  --min-aruco-markers 2 \
  --detected-format png \
  --detected-scale 1.0 \
  --png-compression 9 \
  --keep-rendered-images \
  --dpi 300

echo
echo "============================================================"
echo "6. Recursive bulk grading with automatic filename part labels"
echo "============================================================"

grader "examples/scanned_sheets" \
  --answer-key "$DEMO/input/AnswerKey_demo.xlsx" \
  --part auto \
  --output-folder "$DEMO/bulk_default" \
  --skip-template-generation \
  --metrics-csv-name "grader_metrics_all_files.csv" \
  --detected-format jpg \
  --detected-scale 0.75 \
  --jpeg-quality 82 \
  --min-aruco-markers 2 \
  --dpi 300

echo
echo "============================================================"
echo "7. Explicit part selection and a custom score map"
echo "============================================================"

A_SCAN="$(
  find "examples/scanned_sheets" -type f -iname '*A-1*.pdf' -print | sort | sed -n '1p'
)"

if [[ -n "$A_SCAN" ]]; then
  grader "$A_SCAN" \
    --answer-key "$DEMO/input/AnswerKey_demo.xlsx" \
    --part A \
    --score-map "0:0,1:0.25,2:0.5,3:0.75,4:1" \
    --output-folder "$DEMO/explicit_custom_score" \
    --skip-template-generation \
    --metrics-csv-name "custom_score_metrics.csv" \
    --detected-format webp \
    --detected-scale 0.8 \
    --webp-quality 90 \
    --grader-label "Grader demonstration - custom scoring"
fi

echo
echo "============================================================"
echo "8. Grade a multipage QR PDF using QR-based part resolution"
echo "============================================================"

grader "$DEMO/qr/qr_answer_sheets.pdf" \
  --answer-key "$DEMO/input/AnswerKey_demo.xlsx" \
  --part auto \
  --output-folder "$DEMO/qr_detected" \
  --skip-template-generation \
  --metrics-csv-name "qr_metrics.csv" \
  --detected-format jpg \
  --jpeg-quality 85

echo
echo "============================================================"
echo "9. Optional OCR of the customizable top-left title"
echo "============================================================"

if command -v tesseract >/dev/null 2>&1; then
  grader "$DEMO/qr/qr_answer_sheets.pdf" \
    --answer-key "$DEMO/input/AnswerKey_demo.xlsx" \
    --part auto \
    --read-title-text \
    --title-ocr-language eng \
    --output-folder "$DEMO/title_ocr" \
    --skip-template-generation \
    --metrics-csv-name "title_ocr_metrics.csv"
else
  echo "Tesseract was not found, so the OCR example was skipped."
  echo "On macOS, install it with: brew install tesseract"
fi

echo
echo "============================================================"
echo "10. Summarize generated outputs"
echo "============================================================"

find "$DEMO" -type f | sort

python - <<'PY'
from pathlib import Path
import csv

root = Path("demo_output")
metric_files = sorted(root.rglob("*metrics*.csv"))

print("\nCombined metric files:")
for path in metric_files:
    print(f"\n{path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    if not rows:
        print("  [no rows]")
        continue

    preferred = [
        "SourcePDF",
        "Page",
        "Status",
        "PartLabel",
        "ResolvedPart",
        "PartResolutionSource",
        "PartResolutionStatus",
        "QRText",
        "SheetTitleText",
        "GradingStatus",
        "Score",
        "MaxScore",
        "AccuracyPercent",
        "ScorePercent",
    ]
    columns = [c for c in preferred if c in rows[0]]

    for row in rows[:5]:
        print("  " + " | ".join(f"{c}={row.get(c, '')}" for c in columns))

    if len(rows) > 5:
        print(f"  ... {len(rows) - 5} additional rows")
PY

echo
echo "============================================================"
echo "Demonstration completed"
echo "============================================================"
echo "Outputs: $DEMO"

if command -v open >/dev/null 2>&1; then
  open "$DEMO"
fi
