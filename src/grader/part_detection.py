"""QR, printed-title, and filename-based theory-part resolution."""

import os
import re
import tempfile
import cv2
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pdf2image import convert_from_path

from .config import *
from .geometry import pdf_to_img_xy
from .grading import normalize_part
from .templates import draw_part_title_pdf


def qr_reserved_rect_px(img_w, img_h, pad_pt=8 * MM):
    qr_x_pt = (PDF_W_PT - QR_RESERVED_W_PT) / 2 - pad_pt
    qr_y_pt = PDF_H_PT - MARGIN_Y_PT - QR_RESERVED_H_PT - pad_pt
    qr_w_pt = QR_RESERVED_W_PT + 2 * pad_pt
    qr_h_pt = QR_RESERVED_H_PT + 2 * pad_pt

    p_top_left = pdf_to_img_xy(qr_x_pt, qr_y_pt + qr_h_pt, img_w, img_h)
    p_bottom_right = pdf_to_img_xy(qr_x_pt + qr_w_pt, qr_y_pt, img_w, img_h)

    x1 = max(0, int(round(p_top_left[0])))
    y1 = max(0, int(round(p_top_left[1])))
    x2 = min(img_w, int(round(p_bottom_right[0])))
    y2 = min(img_h, int(round(p_bottom_right[1])))
    return x1, y1, x2, y2


def _decode_qr_in_image(img):
    detector = cv2.QRCodeDetector()

    # OpenCV builds differ. Try multi first, then single.
    try:
        ok, decoded_info, points, straight_qrcode = detector.detectAndDecodeMulti(img)
        if ok and decoded_info:
            for text, pts in zip(decoded_info, points if points is not None else []):
                if text:
                    return text, pts
    except Exception:
        pass

    text, points, straight_qrcode = detector.detectAndDecode(img)
    if text:
        if points is not None:
            return text, points.reshape(-1, 2)
        return text, None

    return "", None


def detect_qr_code(warped):
    img_h, img_w = warped.shape[:2]
    x1, y1, x2, y2 = qr_reserved_rect_px(img_w, img_h)
    crop = warped[y1:y2, x1:x2]

    text, points = _decode_qr_in_image(crop)
    if text:
        if points is not None:
            points = np.array(points, dtype=np.float32)
            points[:, 0] += x1
            points[:, 1] += y1
        return {
            "text": text,
            "status": "detected_reserved_area",
            "points": points,
            "rect": (x1, y1, x2, y2),
        }

    text, points = _decode_qr_in_image(warped)
    if text:
        return {
            "text": text,
            "status": "detected_whole_page",
            "points": points,
            "rect": (x1, y1, x2, y2),
        }

    return {
        "text": "",
        "status": "not_detected",
        "points": None,
        "rect": (x1, y1, x2, y2),
    }


def draw_qr_debug(debug, qr_info):
    x1, y1, x2, y2 = qr_info.get("rect", (0, 0, 0, 0))
    cv2.rectangle(debug, (x1, y1), (x2, y2), IBO_BLUE_BGR, 2)
    points = qr_info.get("points")
    if points is not None:
        pts = np.array(points, dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(debug, [pts], True, IBO_GREEN_BGR, 3)
    label = f"QR: {qr_info.get('status', '')}"
    cv2.putText(debug, label, (x1, max(20, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, IBO_BLUE_BGR, 2)


def crop_pdf_rect_from_image(image, x0_pt, y0_pt, x1_pt, y1_pt):
    """Crop an image using PDF coordinates; PDF origin is bottom-left."""
    img_h, img_w = image.shape[:2]
    p1 = pdf_to_img_xy(x0_pt, y1_pt, img_w, img_h)
    p2 = pdf_to_img_xy(x1_pt, y0_pt, img_w, img_h)

    x0 = int(max(0, min(p1[0], p2[0])))
    x1 = int(min(img_w, max(p1[0], p2[0])))
    y0 = int(max(0, min(p1[1], p2[1])))
    y1 = int(min(img_h, max(p1[1], p2[1])))

    if x1 <= x0 or y1 <= y0:
        return None
    return image[y0:y1, x0:x1].copy()


def crop_printed_part_title_region(warped_image):
    return crop_pdf_rect_from_image(
        warped_image,
        PART_TITLE_CROP_X0_PT,
        PART_TITLE_CROP_Y0_PT,
        PART_TITLE_CROP_X1_PT,
        PART_TITLE_CROP_Y1_PT,
    )


def text_crop_to_binary_mask(crop):
    """Binary mask of dark text: 255 = dark printed text, 0 = background."""
    if crop is None:
        return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return mask


def render_reference_part_crop(part, target_img_w, target_img_h, target_crop_shape):
    """Render the expected title for A/B and crop the same fixed title region."""
    part = normalize_part(part)
    if part not in {"A", "B"}:
        raise ValueError(f"Unknown part for reference render: {part}")

    cache_key = (part, target_img_w, target_img_h, target_crop_shape, DPI)
    if cache_key in _PRINTED_PART_REF_CACHE:
        return _PRINTED_PART_REF_CACHE[cache_key]

    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = os.path.join(tmp_dir, f"_printed_part_ref_{part}.pdf")
        c = canvas.Canvas(pdf_path, pagesize=A4)
        draw_part_title_pdf(c, part)
        c.save()

        pages = convert_from_path(pdf_path, dpi=DPI, first_page=1, last_page=1)
        if not pages:
            raise RuntimeError(f"Could not render reference title for part {part}")

        ref_rgb = np.array(pages[0])
        ref_bgr = cv2.cvtColor(ref_rgb, cv2.COLOR_RGB2BGR)

    if ref_bgr.shape[1] != target_img_w or ref_bgr.shape[0] != target_img_h:
        ref_bgr = cv2.resize(ref_bgr, (target_img_w, target_img_h), interpolation=cv2.INTER_AREA)

    ref_crop = crop_printed_part_title_region(ref_bgr)
    ref_mask = text_crop_to_binary_mask(ref_crop)

    if ref_mask is None:
        raise RuntimeError(f"Could not crop reference title for part {part}")

    if ref_mask.shape != target_crop_shape:
        ref_mask = cv2.resize(ref_mask, (target_crop_shape[1], target_crop_shape[0]), interpolation=cv2.INTER_NEAREST)

    _PRINTED_PART_REF_CACHE[cache_key] = ref_mask
    return ref_mask


def detect_part_from_printout_warped(warped_image):
    """Detect Theory Part A/B from the printed title on the warped sheet.

    This is template matching, not OCR. It compares the printed title region
    against rendered references for "Theory Part A" and "Theory Part B".
    """
    title_crop = crop_printed_part_title_region(warped_image)
    scan_mask = text_crop_to_binary_mask(title_crop)

    if scan_mask is None or np.count_nonzero(scan_mask) < PRINTED_PART_MIN_DARK_PIXELS:
        return {
            "part": None,
            "status": "no_title_detected",
            "score_A": None,
            "score_B": None,
            "confidence": 0.0,
        }

    img_h, img_w = warped_image.shape[:2]
    ref_a = render_reference_part_crop("A", img_w, img_h, scan_mask.shape)
    ref_b = render_reference_part_crop("B", img_w, img_h, scan_mask.shape)

    # Compare mostly where A/B differ so the common "Theory Part " prefix does not dominate.
    diff_zone = cv2.absdiff(ref_a, ref_b)
    kernel = np.ones((5, 5), np.uint8)
    diff_zone = cv2.dilate(diff_zone, kernel, iterations=2)
    diff_pixels = diff_zone > 0

    if np.count_nonzero(diff_pixels) < 20:
        diff_pixels = (ref_a > 0) | (ref_b > 0) | (scan_mask > 0)

    scan01 = scan_mask.astype(np.float32) / 255.0
    refa01 = ref_a.astype(np.float32) / 255.0
    refb01 = ref_b.astype(np.float32) / 255.0

    score_a = float(np.mean(np.abs(scan01[diff_pixels] - refa01[diff_pixels])))
    score_b = float(np.mean(np.abs(scan01[diff_pixels] - refb01[diff_pixels])))

    if score_a < score_b:
        best_part = "A"
        confidence = score_b - score_a
    else:
        best_part = "B"
        confidence = score_a - score_b

    if confidence < PRINTED_PART_MIN_CONFIDENCE:
        return {
            "part": None,
            "status": "low_confidence",
            "score_A": score_a,
            "score_B": score_b,
            "confidence": confidence,
        }

    return {
        "part": best_part,
        "status": "ok",
        "score_A": score_a,
        "score_B": score_b,
        "confidence": confidence,
    }


def draw_printed_part_debug(debug, printed_part_info):
    crop = crop_pdf_rect_from_image(
        debug,
        PART_TITLE_CROP_X0_PT,
        PART_TITLE_CROP_Y0_PT,
        PART_TITLE_CROP_X1_PT,
        PART_TITLE_CROP_Y1_PT,
    )
    img_h, img_w = debug.shape[:2]
    p1 = pdf_to_img_xy(PART_TITLE_CROP_X0_PT, PART_TITLE_CROP_Y1_PT, img_w, img_h)
    p2 = pdf_to_img_xy(PART_TITLE_CROP_X1_PT, PART_TITLE_CROP_Y0_PT, img_w, img_h)
    x0 = int(max(0, min(p1[0], p2[0])))
    x1 = int(min(img_w, max(p1[0], p2[0])))
    y0 = int(max(0, min(p1[1], p2[1])))
    y1 = int(min(img_h, max(p1[1], p2[1])))
    color = IBO_GREEN_BGR if printed_part_info.get("part") else IBO_YELLOW_BGR
    cv2.rectangle(debug, (x0, y0), (x1, y1), color, 2)
    label = f"Printed part: {printed_part_info.get('part') or printed_part_info.get('status', '')}"
    cv2.putText(debug, label, (x0, max(20, y0 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


def infer_part_from_text(*texts):
    joined = " ".join(str(t or "") for t in texts).lower()
    # Prefer explicit wording to avoid matching unrelated A/B letters.
    if re.search(r"part[_\s-]*a|theory[_\s-]*a|\bA\d{2}\b", joined, re.I):
        return "A"
    if re.search(r"part[_\s-]*b|theory[_\s-]*b|\bB\d{2}\b", joined, re.I):
        return "B"
    return None


def infer_part_from_filename_marker(path):
    """Resolve the marking scheme from literal A-1/B-1 markers in a filename.

    Matching is case-insensitive and uses only the base filename. In auto mode,
    this result has priority over the printed-title detector and QR contents.
    """
    filename = os.path.basename(str(path or ""))
    upper_name = filename.upper()
    has_a = "A-1" in upper_name
    has_b = "B-1" in upper_name

    if has_a and has_b:
        return {
            "part": None,
            "status": "ambiguous_both_A-1_and_B-1",
            "filename": filename,
        }
    if has_a:
        return {
            "part": "A",
            "status": "matched_A-1",
            "filename": filename,
        }
    if has_b:
        return {
            "part": "B",
            "status": "matched_B-1",
            "filename": filename,
        }
    return {
        "part": None,
        "status": "no_A-1_or_B-1_marker",
        "filename": filename,
    }


def determine_part_resolution_source(
    requested_part,
    filename_part_info,
    printed_part_info,
    qr_info,
    resolved_part,
):
    """Describe which source supplied the final Theory Part A/B decision."""
    explicit = normalize_part(requested_part)
    if explicit:
        return "explicit_cli_part"
    if not resolved_part:
        return "unresolved"
    if filename_part_info.get("part") == resolved_part:
        return filename_part_info.get("status", "filename_marker")
    if printed_part_info.get("part") == resolved_part:
        return "printed_title"
    if infer_part_from_text(qr_info.get("text", "")) == resolved_part:
        return "qr_text"
    return "other"


def disabled_qr_info(warped):
    img_h, img_w = warped.shape[:2]
    return {
        "text": "",
        "status": "disabled",
        "points": None,
        "rect": qr_reserved_rect_px(img_w, img_h),
    }


def disabled_printed_part_info():
    return {
        "part": None,
        "status": "disabled",
        "score_A": None,
        "score_B": None,
        "confidence": 0.0,
    }
