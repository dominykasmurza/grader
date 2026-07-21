# Algorithm overview

1. Generate or assume fixed A4 template geometry.
2. Detect ArUco markers and align the page using homography or affine fallback.
3. Threshold the aligned image and measure dark-pixel fractions inside answer circles.
4. Classify responses as T, F, empty, or ambiguous.
5. Resolve Part A/B from explicit input, filename, printed title, or QR text.
6. Compare with the answer key and apply the configurable score map.
7. Export annotated images and CSV metrics.

## Validation details to add

- Scanner models: TODO
- Number of sheets reviewed: TODO
- Response-level accuracy: TODO
- False-positive/false-negative rates: TODO
- Missing-marker performance: TODO
