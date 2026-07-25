# Algorithm overview

1. Generate or assume fixed A4 template geometry.
2. Detect ArUco markers and align the page using homography or affine fallback.
3. Optionally decode the QR code and optionally OCR the visible sheet title.
4. Read the distinct `PartLabel` values from column B of the answer key.
5. Resolve one answer-key part label from an explicit CLI value, the filename,
   and/or the QR payload. Filename and QR labels must agree when both are
   present. Visible title OCR is metadata only and never affects grading.
6. Threshold the aligned image and measure dark-pixel fractions inside answer
   circles.
7. Classify responses as T, F, empty, or ambiguous.
8. Select the answer-key rows with the resolved `PartLabel`, compare detected
   responses, and apply the configurable score map.
9. Export annotated images, one detailed per-question CSV, and aggregate CSV
   metrics.

## Part-label matching

Part labels are defined by the answer key rather than hard-coded as A/B. The
preferred answer-key columns are:

- A: question number or question code;
- B: `PartLabel`, repeated for every question;
- D-G: four T/F answers.

With `--part auto`, each known label is matched as a token-bounded literal
substring. This prevents a label such as `A` from matching inside a filename
such as `BRA-123.pdf`.

Examples for the label `Form-Alpha`:

```text
LTU-S1_Form-Alpha_scan.pdf
candidate=LTU-S1&part=Form-Alpha
```

If filename and QR resolve to different labels, the result is reported as a
conflict and grading is not performed silently.

## Validation details

- Scanner models: validated with Sharp BP70C31, BP50C31, MX3061, MX3060, and
  MX2651 devices.
- Smartphone photographs can work when lighting is even and shadows are
  avoided.
- Number of sheets reviewed: 604 sheets at IBO 2026.

## Major identified issues

Eleven of 604 sheets received appeals. The observed issues were associated with
sheet production or marking:

- two sheets had partly removed lower ArUco markers and bottom misalignment;
- approximately five sheets had poorly aligned replacement stickers;
- approximately one sheet used blue pen that was not consistently captured;
- approximately three sheets used dots, crosses, or check marks instead of
  filling the complete circle.
