"""Optional OCR of the customizable sheet-title region.

The detected title is metadata only. It is never used to resolve Part A/B.
"""

import re

import cv2

from .config import *
from .geometry import pdf_to_img_xy


def title_region_rect_px(image):
    """Return the configured title-region rectangle in image coordinates."""
    img_h, img_w = image.shape[:2]
    p1 = pdf_to_img_xy(
        SHEET_TITLE_CROP_X0_PT,
        SHEET_TITLE_CROP_Y1_PT,
        img_w,
        img_h,
    )
    p2 = pdf_to_img_xy(
        SHEET_TITLE_CROP_X1_PT,
        SHEET_TITLE_CROP_Y0_PT,
        img_w,
        img_h,
    )

    x0 = int(max(0, min(p1[0], p2[0])))
    x1 = int(min(img_w, max(p1[0], p2[0])))
    y0 = int(max(0, min(p1[1], p2[1])))
    y1 = int(min(img_h, max(p1[1], p2[1])))
    return x0, y0, x1, y1


def crop_sheet_title_region(warped_image):
    x0, y0, x1, y1 = title_region_rect_px(warped_image)
    if x1 <= x0 or y1 <= y0:
        return None
    return warped_image[y0:y1, x0:x1].copy()


def _preprocess_title_crop(crop):
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(
        gray,
        None,
        fx=TITLE_OCR_SCALE,
        fy=TITLE_OCR_SCALE,
        interpolation=cv2.INTER_CUBIC,
    )
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.threshold(
        gray,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )[1]


def _clean_ocr_text(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def detect_sheet_title_text(warped_image, language=TITLE_OCR_LANGUAGE):
    """Read the visible title using Tesseract OCR.

    Returns a dictionary with ``text``, ``status``, ``confidence``, and ``rect``.
    The result is reporting metadata only and does not affect part resolution.
    """
    rect = title_region_rect_px(warped_image)
    crop = crop_sheet_title_region(warped_image)
    if crop is None or crop.size == 0:
        return {
            "text": "",
            "status": "invalid_crop",
            "confidence": None,
            "rect": rect,
        }

    try:
        import pytesseract
        from pytesseract import Output
    except ImportError:
        return {
            "text": "",
            "status": "pytesseract_not_installed",
            "confidence": None,
            "rect": rect,
        }

    processed = _preprocess_title_crop(crop)
    config = f"--psm {TITLE_OCR_PSM}"

    try:
        data = pytesseract.image_to_data(
            processed,
            lang=language,
            config=config,
            output_type=Output.DICT,
        )
    except pytesseract.TesseractNotFoundError:
        return {
            "text": "",
            "status": "tesseract_not_found",
            "confidence": None,
            "rect": rect,
        }
    except Exception as exc:
        return {
            "text": "",
            "status": f"ocr_error:{type(exc).__name__}",
            "confidence": None,
            "rect": rect,
        }

    words = []
    confidences = []
    for raw_text, raw_conf in zip(data.get("text", []), data.get("conf", [])):
        word = _clean_ocr_text(raw_text)
        if not word:
            continue
        try:
            confidence = float(raw_conf)
        except (TypeError, ValueError):
            confidence = -1.0
        words.append(word)
        if confidence >= 0:
            confidences.append(confidence)

    text = _clean_ocr_text(" ".join(words))
    mean_confidence = (
        round(sum(confidences) / len(confidences), 2)
        if confidences
        else None
    )

    return {
        "text": text,
        "status": "detected" if text else "no_text_detected",
        "confidence": mean_confidence,
        "rect": rect,
    }


def disabled_sheet_title_info(warped_image):
    return {
        "text": "",
        "status": "disabled",
        "confidence": None,
        "rect": title_region_rect_px(warped_image),
    }


def draw_sheet_title_debug(debug, title_info):
    x0, y0, x1, y1 = title_info.get("rect", (0, 0, 0, 0))
    detected = bool(title_info.get("text"))
    color = IBO_GREEN_BGR if detected else IBO_YELLOW_BGR
    cv2.rectangle(debug, (x0, y0), (x1, y1), color, 2)
    label = f"Title OCR: {title_info.get('status', '')}"
    cv2.putText(
        debug,
        label,
        (x0, max(20, y0 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2,
    )
