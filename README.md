# Grader

A Python tool for generating and grading printable optical mark recognition sheets for theory examinations composed of true/false statements.

The grader uses ArUco markers to align scanned pages, detects marked circles, optionally identifies the exam part from the filename, printed title, or QR code, applies configurable nonlinear scoring, and exports annotated images and CSV reports.

## Features

- Printable A4 answer-sheet templates
- Four-, three-, and two-marker ArUco alignment fallback
- Fixed-threshold or Otsu mark detection
- Empty and ambiguous-mark detection
- Optional QR-code reading and printed-title part detection
- Configurable nonlinear scoring
- Recursive bulk processing with mirrored output folders
- Per-sheet and combined CSV metrics
- Compact JPG, PNG, or WebP annotated output

## Installation

Python 3.10+ and Poppler are required.

```bash
git clone https://github.com/TODO_USERNAME/grader.git
cd grader
python -m venv .venv
source .venv/bin/activate
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

## Answer-key format

Column A contains question codes such as `A01` or `B50`; columns D-G contain the four correct T/F answers.

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

Complete `CITATION.cff`, create a GitHub release, and connect the repository to Zenodo for a DOI.

## License

MIT License. See `LICENSE`.

## Disclaimer

Validate detection and grading accuracy before consequential use. The software is provided without warranty.
