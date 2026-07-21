# QR-encoded answer sheets

The `grader-qr` command converts a CSV table into one multipage PDF. Each
non-empty CSV row becomes one answer-sheet page with its own QR code.

## Check the installation

From the repository root:

```bash
conda activate grader
pip install -e .
grader-qr --help
```

## Minimal example

Create `sheets.csv`:

```csv
qr_text
LTU-S1-A
LTU-S2-A
LTU-S3-A
```

Generate the PDF:

```bash
grader-qr sheets.csv qr_answer_sheets.pdf
```

The output contains three pages.

## Recommended CSV format

```csv
qr_text,label,sheet_label
candidate=LTU-S1&part=A,LTU-S1,Theory Examination A
candidate=LTU-S1&part=B,LTU-S1,Theory Examination B
candidate=LTU-S2&part=A,LTU-S2,Practice Examination
```

The columns have separate purposes:

| Column | Purpose |
|---|---|
| `qr_text` | Exact content encoded in the QR code |
| `label` | Optional readable text printed below the QR code |
| `sheet_label` | Optional customizable text printed at the top left |

## Generate sheets using explicit column names

```bash
grader-qr examples/qr_sheets.csv output/qr_answer_sheets.pdf \
  --text-column qr_text \
  --label-column label \
  --sheet-label-column sheet_label \
  --print-text
```

## Use one common top-left label

```bash
grader-qr examples/qr_sheets.csv output/qr_answer_sheets.pdf \
  --default-sheet-label "Biology Examination" \
  --print-text
```

A non-empty `sheet_label` value in the CSV overrides
`--default-sheet-label` for that page.

## QR and text size

The default QR size is 29 mm inside the reserved 30 × 30 mm region. The
default readable-label font size is 9 pt.

```bash
grader-qr examples/qr_sheets.csv output/qr_answer_sheets.pdf \
  --qr-size-mm 29 \
  --qr-label-font-size 9 \
  --print-text
```

Do not set `--qr-size-mm` above 30.

## Error correction

Supported levels are `L`, `M`, `Q`, and `H`:

```bash
grader-qr examples/qr_sheets.csv output/qr_answer_sheets.pdf \
  --error-correction M
```

`M` is the default. Higher levels add redundancy but make the symbol
denser.

## Add a logo

```bash
grader-qr examples/qr_sheets.csv output/qr_answer_sheets.pdf \
  --logo-path path/to/logo.png
```

Omit `--logo-path` to create sheets without a logo.

## Complete example

```bash
grader-qr examples/qr_sheets.csv output/qr_answer_sheets.pdf \
  --text-column qr_text \
  --label-column label \
  --sheet-label-column sheet_label \
  --default-sheet-label "Biology Examination" \
  --qr-size-mm 29 \
  --qr-label-font-size 9 \
  --error-correction M \
  --print-text
```

## Validation before production printing

1. Generate two or three pages.
2. Print at 100% scale; do not use “fit to page.”
3. Scan using the intended scanner workflow.
4. Confirm that all four ArUco markers remain visible.
5. Confirm that the QR code decodes.
6. Confirm that the text below the QR code is not clipped.
7. Run the grader on the scanned test pages.
8. Manually verify the identifiers in the output CSV.

## Data protection

QR payloads may contain identifying information. Do not commit production
CSVs, personalized sheets, answer keys, or confidential identifiers to a
public repository.
