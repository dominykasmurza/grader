# Architecture

The original operational script is divided into focused modules while
preserving a compatibility facade at `grader/grader.py`.

| Module | Responsibility |
|---|---|
| `config.py` | Page dimensions, thresholds, colors, defaults, filenames, and CSV fields |
| `geometry.py` | PDF/image coordinate conversion and answer-circle positions |
| `templates.py` | A4 template, ArUco marker, and mock-sheet generation |
| `qr_sheets.py` | CSV-driven multipage QR answer-sheet generation |
| `alignment.py` | ArUco detection and projective/affine page alignment |
| `part_detection.py` | Answer-key-driven filename and QR part-label resolution |
| `title_detection.py` | Optional OCR of visible sheet-title metadata |
| `grading.py` | Generalized answer-key parsing and configurable nonlinear scoring |
| `visualization.py` | Mark overlays, legends, headers, and image compression |
| `reporting.py` | Detailed and aggregate CSV output |
| `detection.py` | Per-sheet optical mark detection and grading workflow |
| `processing.py` | PDF rendering, recursive discovery, and bulk processing |
| `cli.py` | Argument parsing and executable entry point |

## Part-label data flow

```text
answer key column B ──> known PartLabel values
                              │
filename ─────────────────────┼──> part-label resolver ──> grading lookup
QR payload ───────────────────┘

visible title ──> optional OCR ──> CSV metadata only
```

The resolver reports ambiguity and filename/QR conflicts rather than choosing a
part silently. The resolved label is repeated for every question in the
detailed CSV.

## Dependency direction

```text
config
├── geometry
├── grading
└── templates
    └── alignment

part_detection
 title_detection
visualization
reporting
      ↓
  detection
      ↓
  processing
      ↓
     cli
```

`grader.py` should remain a small compatibility facade rather than becoming a
second implementation.
