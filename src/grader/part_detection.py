"""QR- and filename-based theory-part resolution."""

import os
import re

import cv2
import numpy as np

from .config import *
from .geometry import pdf_to_img_xy
from .grading import normalize_part


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
    cv2.putText(
        debug,
        label,
        (x1, max(20, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        IBO_BLUE_BGR,
        2,
    )


def infer_part_from_text(*texts):
    """Infer A/B only from machine-readable QR text.

    Accepted examples include ``part=A``, ``part:A``, ``part_A``,
    ``part-A``, ``Theory A``, and question-style codes such as ``A01``.
    """
    joined = " ".join(str(t or "") for t in texts)
    if re.search(
        r"\bpart\s*[:=_-]?\s*a\b|\btheory\s*[:=_-]?\s*a\b|\bA\d{2}\b",
        joined,
        re.I,
    ):
        return "A"
    if re.search(
        r"\bpart\s*[:=_-]?\s*b\b|\btheory\s*[:=_-]?\s*b\b|\bB\d{2}\b",
        joined,
        re.I,
    ):
        return "B"
    return None


def infer_part_from_filename_marker(path):
    """Resolve the marking scheme from literal A-1/B-1 filename markers."""
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
    qr_info,
    resolved_part,
):
    """Describe which source supplied the final Part A/B decision."""
    explicit = normalize_part(requested_part)
    if explicit:
        return "explicit_cli_part"
    if not resolved_part:
        return "unresolved"
    if filename_part_info.get("part") == resolved_part:
        return filename_part_info.get("status", "filename_marker")
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
