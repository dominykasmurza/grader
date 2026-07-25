# Grader

A Python tool for generating and grading printable optical mark recognition sheets for theory examinations composed of true/false statements.

The grader uses ArUco markers to align scanned (or photographed and converted to PDF) pages, detects marked circles, resolves an answer-key part label from the filename and/or QR code, applies configurable nonlinear scoring, and exports annotated images and CSV reports. Optional title OCR is metadata only and never controls grading.

Originally developed for International Biology Olympiad 2026 in Vilnius, Lithuania.

## Features

- Printable A4 answer-sheet templates
- Four-, three-, and two-marker ArUco alignment fallback
- Fixed-threshold or Otsu mark detection
- Empty and ambiguous-mark detection
- Answer-key-driven part-label resolution from filenames and QR payloads
- Optional sheet-title OCR for CSV metadata only
- Configurable nonlinear scoring
- Recursive bulk processing with mirrored output folders
- Per-sheet and combined CSV metrics
- Compact JPG, PNG, or WebP annotated output
- Stickers can be used for resetting the answer fields to empty
- The sticker design has bigger circles than original sheet to allow some sticker application error margin

## Installation

Python 3.10+ and Poppler are required.

```bash
git clone https://github.com/dominykasmurza/grader.git
cd grader
conda activate grader
pip install -e .
```

On macOS, install Poppler with `brew install poppler`. On Ubuntu/Debian use `sudo apt-get install poppler-utils`.

## Quick start

Generate templates:

```bash
grader --template-only
```

Process one PDF:

```bash
grader scanned_sheet.pdf --output-folder output --skip-template-generation
```

Process a folder recursively:

```bash
grader scanned_sheets --output-folder bulk_detected --skip-template-generation
```

Grade with an Excel answer key:

```bash
grader scanned_sheets --answer-key examples/synthetic_answer_key.xlsx --part auto --output-folder bulk_detected --skip-template-generation
```

## Full functionality demo

Upon installation, run:

```bash
bash ~/grader/run_all_grader_examples.sh ~/grader
```

The output will be in the directory `grader/demo_output`

## Answer-key format

The preferred Excel layout is:

| Column | Content |
|---|---|
| A | Question number or question code |
| B | `PartLabel`, repeated for every question |
| C | Optional/unused |
| D-G | Correct T/F answers for statements 1-4 |

Example:

| Question | PartLabel |  | Answer1 | Answer2 | Answer3 | Answer4 |
|---:|---|---|---|---|---|---|
| 1 | Form-Alpha |  | T | F | T | F |
| 2 | Form-Alpha |  | F | F | T | T |
| 1 | Form-Beta |  | T | T | F | F |

`PartLabel` may be any short, distinctive text. With `--part auto`, the grader searches for the labels defined in column B as token-bounded substrings in the input filename and QR payload. If both sources contain a label, they must agree. Conflicts and ambiguous matches are reported and the sheet is not graded silently.

Legacy answer keys with codes such as `A01` or `B50` in column A and a blank column B remain supported.

### Filename and QR examples

For an answer-key label `Form-Alpha`, either of these can resolve the part:

```text
LTU-S1_Form-Alpha_scan.pdf
candidate=LTU-S1&part=Form-Alpha
```

Run automatic resolution with:

```bash
grader scanned_sheets   --answer-key AnswerKey.xlsx   --part auto   --output-folder bulk_detected   --skip-template-generation
```

Or override it explicitly with an exact answer-key label:

```bash
grader scanned_sheets --answer-key AnswerKey.xlsx --part "Form-Alpha"
```

Each question row in the detailed CSV contains `PartLabel`, along with `PartResolutionSource`, `PartResolutionStatus`, filename/QR matches, and `GradingStatus`.

## Default scoring

| Correct statements | Score |
|---:|---:|
| 0 | 0.0 |
| 1 | 0.2 |
| 2 | 0.4 |
| 3 | 0.6 |
| 4 | 1.0 |

Override it with `--score-map`.

## Privacy and security

Do not commit personalized candidate sheets, identifying QR data, confidential examinations or answer keys, internal operational documents, or logos without permission.

## Known limitation

The public CLI currently accepts PDF-content files. The underlying image function can read JPG/PNG files, but direct image input is not yet wired into the CLI.

## Authorship

Developed by **Dominykas Murza**.

- Affiliation: Life Sciences Center, Vilnius University, Lithuania
- ORCID: https://orcid.org/0009-0004-8204-5233

## Citation

Please see `CITATION.cff`.

## License

MIT License. See `LICENSE`.

## Disclaimer

Validate detection and grading accuracy before consequential use. The software is provided without warranty.
## QR-encoded answer-sheet generation

The separate `grader-qr` command creates a multipage PDF from a CSV file.
Each non-empty row produces one answer-sheet page.

```csv
qr_text,label,sheet_label
candidate=LTU-S1&part=A,LTU-S1,Theory Examination A
candidate=LTU-S1&part=B,LTU-S1,Theory Examination B
```

```bash
grader-qr examples/qr_sheets.csv output/qr_answer_sheets.pdf \
  --text-column qr_text \
  --label-column label \
  --sheet-label-column sheet_label \
  --qr-size-mm 29 \
  --qr-label-font-size 9 \
  --error-correction M \
  --print-text
```

Use `--default-sheet-label "Your label"` to apply one common
top-left label. See [`docs/QR_SHEETS.md`](docs/QR_SHEETS.md) for all
options and production-validation guidance.
