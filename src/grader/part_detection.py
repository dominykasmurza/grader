"""QR- and filename-based answer-key part-label resolution."""

import os
import re
from urllib.parse import unquote_plus

import cv2
import numpy as np

from .config import *
from .geometry import pdf_to_img_xy
from .grading import canonical_part_label, normalize_part_label


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


def _unique_part_labels(part_labels):
    labels = []
    seen = set()
    for raw_label in part_labels or []:
        label = normalize_part_label(raw_label)
        canonical = canonical_part_label(label)
        if canonical and canonical not in seen:
            seen.add(canonical)
            labels.append(label)
    return labels


def _exact_known_label(value, part_labels):
    target = canonical_part_label(unquote_plus(str(value or "")).strip())
    if not target:
        return None
    for label in _unique_part_labels(part_labels):
        if canonical_part_label(label) == target:
            return label
    return None


def _token_matches(text, part_labels):
    """Find configured labels as literal, token-bounded substrings.

    Token boundaries prevent a one-letter label such as ``A`` from matching a
    country or candidate code such as ``BRA-123``. When overlapping labels
    match at the same location, the longest configured label wins.
    """
    source = str(text or "")
    hits = []
    for label in _unique_part_labels(part_labels):
        pattern = re.compile(
            rf"(?<![A-Za-z0-9]){re.escape(label)}(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        for match in pattern.finditer(source):
            hits.append((match.start(), match.end(), label))

    if not hits:
        return []

    # Suppress shorter labels nested inside a longer label at the same span.
    selected = []
    for start, end, label in hits:
        contained_by_longer = any(
            other_start <= start
            and other_end >= end
            and (other_end - other_start) > (end - start)
            for other_start, other_end, _ in hits
        )
        if not contained_by_longer:
            selected.append(label)

    unique = []
    seen = set()
    for label in selected:
        canonical = canonical_part_label(label)
        if canonical not in seen:
            seen.add(canonical)
            unique.append(label)
    return unique


def _resolution_info(matches, source, no_match_status):
    matches = _unique_part_labels(matches)
    if len(matches) == 1:
        return {
            "part": matches[0],
            "matches": matches,
            "status": f"matched_{source}",
        }
    if len(matches) > 1:
        return {
            "part": None,
            "matches": matches,
            "status": f"ambiguous_{source}_labels",
        }
    return {
        "part": None,
        "matches": [],
        "status": no_match_status,
    }


def infer_part_label_from_filename(path, part_labels):
    """Match one configured answer-key part label in the filename."""
    filename = os.path.basename(str(path or ""))
    info = _resolution_info(
        _token_matches(filename, part_labels),
        source="filename",
        no_match_status="no_part_label_in_filename",
    )
    info["filename"] = filename
    return info


def _explicit_qr_part_values(text):
    values = re.findall(
        r"(?:^|[?&;,\s])part(?:_label)?\s*[:=]\s*([^&;,\s]+)",
        str(text or ""),
        flags=re.IGNORECASE,
    )
    return [unquote_plus(value).strip() for value in values if value.strip()]


def infer_part_label_from_qr_text(text, part_labels):
    """Match one configured part label in QR text.

    Explicit ``part=...`` or ``part_label=...`` values are preferred. If no
    such key is present, the function falls back to token-bounded substring
    matching against the complete QR payload.
    """
    explicit_values = _explicit_qr_part_values(text)
    if explicit_values:
        matches = [
            matched
            for value in explicit_values
            if (matched := _exact_known_label(value, part_labels)) is not None
        ]
        info = _resolution_info(
            matches,
            source="qr",
            no_match_status="qr_part_value_not_in_answer_key",
        )
        info["explicit_values"] = explicit_values
        return info

    info = _resolution_info(
        _token_matches(text, part_labels),
        source="qr",
        no_match_status="no_part_label_in_qr",
    )
    info["explicit_values"] = []
    return info


def resolve_part_label(requested_part, source_name, qr_text, part_labels):
    """Resolve a grading part label from explicit input, filename, or QR.

    Automatic resolution is answer-key driven: only labels found in the answer
    key are eligible. Filename and QR results must agree when both are present.
    """
    known_labels = _unique_part_labels(part_labels)
    requested_text = str(requested_part or "").strip()

    if requested_text and requested_text.casefold() != "auto":
        explicit = _exact_known_label(requested_text, known_labels)
        if explicit is None:
            return {
                "part": None,
                "source": "explicit_cli_part",
                "status": "explicit_part_not_in_answer_key",
                "filename": infer_part_label_from_filename(source_name, known_labels),
                "qr": infer_part_label_from_qr_text(qr_text, known_labels),
            }
        return {
            "part": explicit,
            "source": "explicit_cli_part",
            "status": "resolved_explicit_cli_part",
            "filename": infer_part_label_from_filename(source_name, known_labels),
            "qr": infer_part_label_from_qr_text(qr_text, known_labels),
        }

    filename_info = infer_part_label_from_filename(source_name, known_labels)
    qr_info = infer_part_label_from_qr_text(qr_text, known_labels)

    if filename_info["status"].startswith("ambiguous_"):
        return {
            "part": None,
            "source": "filename",
            "status": filename_info["status"],
            "filename": filename_info,
            "qr": qr_info,
        }
    if qr_info["status"].startswith("ambiguous_"):
        return {
            "part": None,
            "source": "qr_text",
            "status": qr_info["status"],
            "filename": filename_info,
            "qr": qr_info,
        }

    filename_part = filename_info.get("part")
    qr_part = qr_info.get("part")
    if filename_part and qr_part:
        if canonical_part_label(filename_part) != canonical_part_label(qr_part):
            return {
                "part": None,
                "source": "filename_and_qr",
                "status": "filename_qr_part_conflict",
                "filename": filename_info,
                "qr": qr_info,
            }
        return {
            "part": filename_part,
            "source": "filename_and_qr",
            "status": "resolved_filename_and_qr_agree",
            "filename": filename_info,
            "qr": qr_info,
        }
    if filename_part:
        return {
            "part": filename_part,
            "source": "filename",
            "status": "resolved_filename",
            "filename": filename_info,
            "qr": qr_info,
        }
    if qr_part:
        return {
            "part": qr_part,
            "source": "qr_text",
            "status": "resolved_qr",
            "filename": filename_info,
            "qr": qr_info,
        }
    return {
        "part": None,
        "source": "unresolved",
        "status": "no_answer_key_part_label_matched",
        "filename": filename_info,
        "qr": qr_info,
    }


# Backward-compatible A/B helpers retained for external callers.
def infer_part_from_text(*texts):
    joined = " ".join(str(text or "") for text in texts)
    return infer_part_label_from_qr_text(joined, ["A", "B"]).get("part")


def infer_part_from_filename_marker(path):
    info = infer_part_label_from_filename(path, ["A", "B"])
    return {
        "part": info.get("part"),
        "status": info.get("status", ""),
        "filename": info.get("filename", os.path.basename(str(path or ""))),
    }


def determine_part_resolution_source(
    requested_part,
    filename_part_info,
    qr_info,
    resolved_part,
):
    explicit = normalize_part_label(requested_part)
    if explicit:
        return "explicit_cli_part"
    if not resolved_part:
        return "unresolved"
    if canonical_part_label(filename_part_info.get("part")) == canonical_part_label(resolved_part):
        return "filename"
    if canonical_part_label(infer_part_from_text(qr_info.get("text", ""))) == canonical_part_label(resolved_part):
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
