# QR-encoded answer sheets

The `grader-qr` command reads a CSV and creates one multipage PDF. Each
non-empty row becomes one answer-sheet page with its own QR code.

## Minimal CSV

```csv
qr_text
LTU-S1
LTU-S2
LTU-S3
```

Run:

```bash
grader-qr students.csv qr_answer_sheets.pdf --default-part A
```

## CSV with separate parts and labels

```csv
qr_text,part,label
LTU-S1-A,A,LTU-S1
LTU-S1-B,B,LTU-S1
LTU-S2-A,A,LTU-S2
LTU-S2-B,B,LTU-S2
```

Run:

```bash
grader-qr sheets.csv encoded_sheets.pdf \
  --text-column qr_text \
  --part-column part \
  --label-column label \
  --print-text
```

Recognized QR-text column names include `qr_text`, `qr`, `code`, `text`,
`payload`, and `student_code`. Empty rows are skipped.

The QR code is vector-based and placed inside the existing 30 x 30 mm reserved
area. The default code size is 26 mm with error-correction level M.
