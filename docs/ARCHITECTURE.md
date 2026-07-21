# Architecture

The original operational script has been divided into focused modules while
preserving a compatibility facade at `grader/grader.py`.

| Module | Responsibility |
|---|---|
| `config.py` | Page dimensions, thresholds, colors, defaults, and filenames |
| `geometry.py` | PDF/image coordinate conversion and answer-circle positions |
| `templates.py` | A4 template, ArUco marker, and mock-sheet generation |
| `qr_sheets.py` | CSV-driven multipage QR answer-sheet generation |
| `alignment.py` | ArUco detection and projective/affine page alignment |
| `part_detection.py` | QR, printed-title, and filename part resolution |
| `grading.py` | Answer-key parsing and configurable nonlinear scoring |
| `visualization.py` | Mark overlays, legends, headers, and image compression |
| `reporting.py` | Detailed and aggregate CSV output |
| `detection.py` | Per-sheet optical mark detection workflow |
| `processing.py` | PDF rendering, recursive discovery, and bulk processing |
| `cli.py` | Argument parsing and executable entry point |

## Dependency direction

```text
config
  ├── geometry
  ├── grading
  └── templates
        └── alignment

part_detection
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
