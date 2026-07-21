"""Annotated-image overlays and compressed visual output."""

import os
import cv2

from .config import *
from .geometry import pdf_len_to_px
from .grading import format_score


def draw_grading_overlay(debug, centers, detected_rows, graded_rows, details, radius_px):
    """Draw grading overlay.

    Green is used only for the mark that was actually detected and is correct.
    Wrong detected marks are red only; the correct cell is not highlighted.
    Empty/missing cells use yellow; ambiguous cells use purple.
    """
    graded_by_q = {row["question"]: row for row in graded_rows}

    for q_idx, row_centers in enumerate(centers, start=1):
        graded = graded_by_q.get(q_idx)
        if not graded:
            continue

        for s_idx, item in enumerate(row_centers):
            detected = detected_rows[q_idx - 1][s_idx]
            result = graded["result"][s_idx]
            detail = details[q_idx - 1][s_idx]

            x = item["x"]
            y_detected = item["y_t"] if detected == "T" else item["y_f"] if detected == "F" else None

            if result == "correct" and y_detected is not None:
                cv2.circle(debug, (x, y_detected), radius_px + 3, IBO_GREEN_BGR, 4)
            elif result == "incorrect" and y_detected is not None:
                cv2.circle(debug, (x, y_detected), radius_px + 3, IBO_RED_BGR, 4)
            elif result == "missing":
                ambiguous = bool(detail.get("ambiguous"))
                color = IBO_PURPLE_BGR if ambiguous else IBO_YELLOW_BGR
                cv2.circle(debug, (x, item["y_t"]), radius_px + 2, color, 5)
                cv2.circle(debug, (x, item["y_f"]), radius_px + 2, color, 5)
            elif result == "no_key":
                # No reference answer for this cell: show detected mark, if any, in blue.
                if y_detected is not None:
                    cv2.circle(debug, (x, y_detected), radius_px + 3, IBO_BLUE_BGR, 3)


def draw_question_score_overlay(debug, centers, graded_rows, radius_px):
    """Print each question's nonlinear score next to its group of four statements."""
    img_h, img_w = debug.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.8
    thickness = 2
    pad = 4
    page_margin_px = int(round(pdf_len_to_px(4 * MM, img_w, img_h)))

    for graded in graded_rows:
        q_idx = int(graded["question"])
        if q_idx < 1 or q_idx > len(centers):
            continue

        row_centers = centers[q_idx - 1]
        if not row_centers:
            continue

        text = format_score(graded.get("score", 0.0))
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)

        last_item = row_centers[-1]
        first_item = row_centers[0]
        y_mid = int(round((last_item["y_t"] + last_item["y_f"]) / 2))
        x = int(round(last_item["x"] + radius_px + 8))
        y = int(round(y_mid + th / 2))

        # If this would run off the page, place it to the left of the first cell.
        if x + tw + pad > img_w - page_margin_px:
            x = int(round(first_item["x"] - radius_px - tw - 8))

        bg_x0 = max(0, x - pad)
        bg_y0 = max(0, y - th - pad)
        bg_x1 = min(img_w - 1, x + tw + pad)
        bg_y1 = min(img_h - 1, y + baseline + pad)
        cv2.rectangle(debug, (bg_x0, bg_y0), (bg_x1, bg_y1), (255, 255, 255), -1)
        cv2.putText(debug, text, (x, y), font, scale, IBO_BLUE_BGR, thickness, cv2.LINE_AA)


def draw_total_score_overlay(debug, grade_metrics):
    """Print total nonlinear score at the bottom-right side of the detected PNG."""
    img_h, img_w = debug.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 1.0
    thickness = 3
    pad = 10

    score = grade_metrics.get("score", 0.0)
    max_score = grade_metrics.get("max_score", 0.0)
    text = f"Total: {format_score(score)} / {format_score(max_score)}"
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)

    margin_x = int(round(pdf_len_to_px(MARGIN_X_PT * 0.65, img_w, img_h)))
    # Above the bottom legend, still clearly in the bottom-right area.
    y = img_h - int(round(pdf_len_to_px(MARGIN_Y_PT * 0.75, img_w, img_h)))
    x = img_w - margin_x - tw

    bg_x0 = max(0, x - pad)
    bg_y0 = max(0, y - th - pad)
    bg_x1 = min(img_w - 1, x + tw + pad)
    bg_y1 = min(img_h - 1, y + baseline + pad)
    cv2.rectangle(debug, (bg_x0, bg_y0), (bg_x1, bg_y1), (255, 255, 255), -1)
    cv2.putText(debug, text, (x, y), font, scale, IBO_BLUE_BGR, thickness, cv2.LINE_AA)


def draw_bottom_legend(debug, graded_mode=True):
    """Draw the colour key at the bottom of the visualized sheet."""
    img_h, img_w = debug.shape[:2]
    y = img_h - int(round(pdf_len_to_px(MARGIN_Y_PT * 0.35, img_w, img_h)))
    x = int(round(pdf_len_to_px(MARGIN_X_PT + ARUCO_SIZE_PT + 8 * MM, img_w, img_h)))
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.75
    thickness = 2
    pad = 8

    items = [
        ("green = correct", IBO_GREEN_BGR),
        ("red = incorrect", IBO_RED_BGR),
        ("yellow = empty", IBO_YELLOW_BGR),
        ("purple = both circles marked", IBO_PURPLE_BGR),
    ]
    if not graded_mode:
        items.append(("blue = detected/ungraded", IBO_BLUE_BGR))

    total_w = 0
    sizes = []
    for text, _ in items:
        (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
        sizes.append((tw, th, baseline))
        total_w += tw + 24

    max_h = max(th + baseline for _, th, baseline in sizes)
    bg_x0 = max(0, x - pad)
    bg_y0 = max(0, y - max_h - pad)
    bg_x1 = min(img_w - 1, x + total_w + pad)
    bg_y1 = min(img_h - 1, y + pad)
    cv2.rectangle(debug, (bg_x0, bg_y0), (bg_x1, bg_y1), (255, 255, 255), -1)

    cursor = x
    for (text, color), (tw, th, baseline) in zip(items, sizes):
        cv2.putText(debug, text, (cursor, y), font, scale, color, thickness, cv2.LINE_AA)
        cursor += tw + 24


def draw_grader_header(debug, timestamp_text="", grader_text=GRADER_HEADER_TEXT):
    """Draw grader name and an optional timestamp at the top of a detected sheet."""
    img_h, img_w = debug.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX

    scale_factor = max(0.55, img_w / 2500.0)
    header_scale = 0.85 * scale_factor
    timestamp_scale = 0.52 * scale_factor
    header_thickness = max(1, int(round(2 * scale_factor)))
    timestamp_thickness = max(1, int(round(1.5 * scale_factor)))
    pad = max(6, int(round(8 * scale_factor)))

    (header_w, header_h), header_base = cv2.getTextSize(
        grader_text, font, header_scale, header_thickness
    )
    header_x = max(0, (img_w - header_w) // 2)
    header_y = max(header_h + pad, int(round(0.018 * img_h)))

    timestamp_w = timestamp_h = timestamp_base = 0
    if timestamp_text:
        (timestamp_w, timestamp_h), timestamp_base = cv2.getTextSize(
            timestamp_text, font, timestamp_scale, timestamp_thickness
        )

    box_w = max(header_w, timestamp_w)
    box_h = header_h + header_base
    if timestamp_text:
        box_h += timestamp_h + timestamp_base + pad

    box_x0 = max(0, (img_w - box_w) // 2 - pad)
    box_y0 = max(0, header_y - header_h - pad)
    box_x1 = min(img_w - 1, (img_w + box_w) // 2 + pad)
    box_y1 = min(img_h - 1, box_y0 + box_h + 2 * pad)
    cv2.rectangle(debug, (box_x0, box_y0), (box_x1, box_y1), (255, 255, 255), -1)

    cv2.putText(
        debug,
        grader_text,
        (header_x, header_y),
        font,
        header_scale,
        IBO_GREY_BGR,
        header_thickness,
        cv2.LINE_AA,
    )

    if timestamp_text:
        timestamp_x = max(0, (img_w - timestamp_w) // 2)
        timestamp_y = header_y + timestamp_h + pad
        cv2.putText(
            debug,
            timestamp_text,
            (timestamp_x, timestamp_y),
            font,
            timestamp_scale,
            IBO_BLUE_BGR,
            timestamp_thickness,
            cv2.LINE_AA,
        )


def normalize_detected_output_format(value):
    value = str(value or DETECTED_OUTPUT_FORMAT).strip().lower()
    if value == "jpeg":
        value = "jpg"
    if value not in {"jpg", "png", "webp"}:
        raise ValueError("Detected output format must be jpg, png, or webp")
    return value


def detected_output_extension(value):
    return normalize_detected_output_format(value)


def save_detected_visual(
    path,
    image,
    scale=DETECTED_OUTPUT_SCALE,
    jpeg_quality=DETECTED_JPEG_QUALITY,
    webp_quality=DETECTED_WEBP_QUALITY,
    png_compression=DETECTED_PNG_COMPRESSION,
):
    """Save the annotated sheet with controllable dimensions and compression."""
    try:
        scale = float(scale)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid detected output scale: {scale}") from exc
    if scale <= 0 or scale > 1:
        raise ValueError("Detected output scale must be > 0 and <= 1")

    output = image
    if scale < 0.999:
        new_w = max(1, int(round(image.shape[1] * scale)))
        new_h = max(1, int(round(image.shape[0] * scale)))
        output = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    ext = os.path.splitext(path)[1].lower()
    if ext in {".jpg", ".jpeg"}:
        params = [cv2.IMWRITE_JPEG_QUALITY, max(1, min(100, int(jpeg_quality)))]
    elif ext == ".webp":
        params = [cv2.IMWRITE_WEBP_QUALITY, max(1, min(100, int(webp_quality)))]
    elif ext == ".png":
        params = [cv2.IMWRITE_PNG_COMPRESSION, max(0, min(9, int(png_compression)))]
    else:
        raise ValueError(f"Unsupported detected output extension: {ext}")

    ok = cv2.imwrite(path, output, params)
    if not ok:
        raise RuntimeError(f"Could not save detected visual: {path}")
    return {
        "path": path,
        "width": output.shape[1],
        "height": output.shape[0],
        "scale": scale,
        "size_bytes": os.path.getsize(path),
    }
