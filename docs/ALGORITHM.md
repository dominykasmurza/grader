# Algorithm overview

1. Generate or assume fixed A4 template geometry.
2. Detect ArUco markers and align the page using homography or affine fallback.
3. Threshold the aligned image and measure dark-pixel fractions inside answer circles.
4. Classify responses as T, F, empty, or ambiguous.
5. Resolve Part A/B from explicit input, filename, printed title, or QR text.
6. Compare with the answer key and apply the configurable score map.
7. Export annotated images and CSV metrics.

## Validation details to add

- Scanner models: Validated with Sharp printers/scanners (BP70C31, BP50C31, MX3061, MX3060, MX2651), also works with pictures from smartphones, but even lighting needs to be ensured (avoid shadow).
- Number of sheets reviewed: 604 sheets were evaluated at the IBO 2026.

## Major identified issues

11 sheets out of 604 received appeals and issues were all caused by the user side:

- Poor performance when the two bottom ArUco markers were partly removed due to printing (2 sheets; misaligned bottom).
- Improper sticker alignment (scores were adjusted for ~5 sheets due to bad sticker alignment).
- Use of blue pen (some of the blue-marked circles were not captured, ~1 sheet).
- Not filling the whole circle (e.g. using dots, "x", check marks, ~3 sheets).
