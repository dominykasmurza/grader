"""Mark detection and single-sheet grading workflow."""

from datetime import datetime
import cv2
import numpy as np

from .config import *
from .alignment import warp_with_markers
from .geometry import square_centers_px, pdf_len_to_px
from .grading import (
    format_score,
    grade_detected_rows,
    normalize_score_map,
)
from .grading import normalize_part
from .part_detection import (
    detect_part_from_printout_warped,
    detect_qr_code,
    disabled_printed_part_info,
    disabled_qr_info,
    draw_printed_part_debug,
    draw_qr_debug,
    infer_part_from_filename_marker,
    infer_part_from_text,
)
from .reporting import write_detailed_sheet_csv
from .visualization import (
    draw_bottom_legend,
    draw_grader_header,
    draw_grading_overlay,
    draw_question_score_overlay,
    draw_total_score_overlay,
    save_detected_visual,
)


def safe_crop(img, x, y, half_side):
    h, w = img.shape[:2]
    x1, x2 = x - half_side, x + half_side
    y1, y2 = y - half_side, y + half_side
    if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
        return None
    return img[y1:y2, x1:x2]


def _run_detection_on_image(
    image,
    vis_path,
    csv_path,
    rendered_png_path=None,
    answer_key=None,
    part=None,
    source_name="",
    page_number=1,
    score_map=None,
    enable_part_detector=ENABLE_PART_DETECTOR,
    enable_qr_reader=ENABLE_QR_READER,
    add_timestamp=ADD_TIMESTAMP_TO_DETECTED,
    grader_text=GRADER_HEADER_TEXT,
    min_aruco_markers=MIN_ARUCO_MARKERS,
    detected_scale=DETECTED_OUTPUT_SCALE,
    jpeg_quality=DETECTED_JPEG_QUALITY,
    webp_quality=DETECTED_WEBP_QUALITY,
    png_compression=DETECTED_PNG_COMPRESSION,
):
    warped, src_pts, dst_pts, found, alignment_info = warp_with_markers(
        image, min_markers=min_aruco_markers
    )

    qr_info = detect_qr_code(warped) if enable_qr_reader else disabled_qr_info(warped)
    printed_part_info = (
        detect_part_from_printout_warped(warped)
        if enable_part_detector
        else disabled_printed_part_info()
    )

    # Explicit --part A/B always wins. In auto mode, literal filename markers
    # A-1 and B-1 have first priority, independently of the optional readers.
    # Printed-title and QR detection are then used as fallbacks when enabled.
    filename_part_info = infer_part_from_filename_marker(source_name)
    resolved_part = normalize_part(part)
    if resolved_part is None and str(part).strip().lower() == "auto":
        resolved_part = filename_part_info.get("part")
        if resolved_part is None and enable_part_detector:
            resolved_part = printed_part_info.get("part")
        if resolved_part is None and enable_qr_reader:
            resolved_part = infer_part_from_text(qr_info.get("text", ""))

    timestamp_text = (
        datetime.now().astimezone().strftime(TIMESTAMP_FORMAT)
        if add_timestamp
        else ""
    )

    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    if USE_FIXED_DARK_THRESHOLD:
        binary_inv = np.zeros_like(blurred, dtype=np.uint8)
        binary_inv[blurred <= DARK_PIXEL_THRESHOLD] = 255
    else:
        _, binary_inv = cv2.threshold(
            blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

    img_h, img_w = gray.shape[:2]
    diameter_px = int(round(pdf_len_to_px(ANSWER_CIRCLE_DIAMETER_PT, img_w, img_h)))
    radius_px = max(6, diameter_px // 2)
    inner_r = max(5, radius_px - 3)

    mask = np.zeros((2 * inner_r, 2 * inner_r), dtype=np.uint8)
    cv2.circle(mask, (inner_r, inner_r), inner_r, 255, -1)
    mask_n = float(np.count_nonzero(mask))

    centers = square_centers_px(img_w, img_h)

    detected_rows = []
    detail_rows = []
    metrics = {
        "total_cells": 0,
        "detected_T": 0,
        "detected_F": 0,
        "empty": 0,
        "ambiguous": 0,
    }

    debug = warped.copy()

    # Show the marker(s) actually used for alignment.
    for marker_name in alignment_info.get("marker_names", []):
        marker_id = ARUCO_IDS[marker_name]
        pts = np.round(found[marker_id]).astype(np.int32)
        cv2.polylines(debug, [pts.reshape(-1, 1, 2)], True, IBO_YELLOW_BGR, 3)
        center = tuple(np.round(pts.mean(axis=0)).astype(int))
        cv2.putText(
            debug,
            f"{marker_name}*",
            (center[0] + 6, center[1]),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            IBO_GREY_BGR,
            2,
        )

    if enable_qr_reader:
        draw_qr_debug(debug, qr_info)
    if enable_part_detector:
        draw_printed_part_debug(debug, printed_part_info)

    for row in centers:
        detected = []
        detail_row = []

        for item in row:
            x = item["x"]
            y_t = item["y_t"]
            y_f = item["y_f"]

            roi_t = safe_crop(binary_inv, x, y_t, inner_r)
            roi_f = safe_crop(binary_inv, x, y_f, inner_r)

            metrics["total_cells"] += 1

            if roi_t is None or roi_f is None:
                detected.append("")
                detail_row.append({
                    "dark_t": None,
                    "dark_f": None,
                    "ambiguous": False,
                })
                metrics["empty"] += 1
                continue

            dark_t = np.count_nonzero(roi_t[mask == 255]) / mask_n
            dark_f = np.count_nonzero(roi_f[mask == 255]) / mask_n
            ambiguous = False

            if dark_t >= MIN_FILL_FRACTION and (dark_t - dark_f) >= MIN_FILL_DIFF:
                detected.append("T")
                metrics["detected_T"] += 1
            elif dark_f >= MIN_FILL_FRACTION and (dark_f - dark_t) >= MIN_FILL_DIFF:
                detected.append("F")
                metrics["detected_F"] += 1
            else:
                detected.append("")
                metrics["empty"] += 1
                if max(dark_t, dark_f) >= MIN_FILL_FRACTION:
                    metrics["ambiguous"] += 1
                    ambiguous = True

            detail_row.append({
                "dark_t": dark_t,
                "dark_f": dark_f,
                "ambiguous": ambiguous,
            })

        detected_rows.append(detected)
        detail_rows.append(detail_row)

    answer_key = answer_key or {}
    graded_rows = []
    grade_metrics = {
        "gradable_cells": 0,
        "correct": 0,
        "incorrect": 0,
        "missing": 0,
        "ambiguous": metrics["ambiguous"],
        "score": 0.0,
        "max_score": 0.0,
        "linear_correct_cells": 0,
        "question_count": 0,
    }

    if answer_key and resolved_part:
        graded_rows, grade_metrics = grade_detected_rows(
            detected_rows,
            answer_key,
            resolved_part,
            score_map=score_map,
        )
        grade_metrics["ambiguous"] = metrics["ambiguous"]
        draw_grading_overlay(
            debug,
            centers,
            detected_rows,
            graded_rows,
            detail_rows,
            radius_px,
        )
        draw_question_score_overlay(debug, centers, graded_rows, radius_px)
        draw_total_score_overlay(debug, grade_metrics)
    else:
        for q_idx, row in enumerate(centers):
            for s_idx, item in enumerate(row):
                detected = detected_rows[q_idx][s_idx]
                detail = detail_rows[q_idx][s_idx]
                if detected == "T":
                    cv2.circle(
                        debug,
                        (item["x"], item["y_t"]),
                        radius_px,
                        IBO_BLUE_BGR,
                        2,
                    )
                elif detected == "F":
                    cv2.circle(
                        debug,
                        (item["x"], item["y_f"]),
                        radius_px,
                        IBO_BLUE_BGR,
                        2,
                    )
                else:
                    color = (
                        IBO_PURPLE_BGR
                        if detail.get("ambiguous")
                        else IBO_YELLOW_BGR
                    )
                    cv2.circle(
                        debug,
                        (item["x"], item["y_t"]),
                        radius_px,
                        color,
                        1,
                    )
                    cv2.circle(
                        debug,
                        (item["x"], item["y_f"]),
                        radius_px,
                        color,
                        1,
                    )

    draw_bottom_legend(
        debug,
        graded_mode=bool(answer_key and resolved_part),
    )
    draw_grader_header(
        debug,
        timestamp_text=timestamp_text,
        grader_text=grader_text,
    )

    write_detailed_sheet_csv(
        csv_path=csv_path,
        source_name=source_name,
        page_number=page_number,
        detected_rows=detected_rows,
        metrics=metrics,
        qr_info=qr_info,
        printed_part_info=printed_part_info,
        alignment_info=alignment_info,
        resolved_part=resolved_part,
        graded_rows=graded_rows,
        grade_metrics=grade_metrics,
        timestamp_text=timestamp_text,
        grader_text=grader_text,
    )
    detected_save_info = save_detected_visual(
        vis_path,
        debug,
        scale=detected_scale,
        jpeg_quality=jpeg_quality,
        webp_quality=webp_quality,
        png_compression=png_compression,
    )

    if rendered_png_path is not None:
        print(f"Rendered intermediate: {rendered_png_path}")
    print(f"Detected file saved: {vis_path}")
    print(
        f"  Saved size: {detected_save_info['size_bytes'] / (1024 * 1024):.2f} MiB; "
        f"dimensions: {detected_save_info['width']} x {detected_save_info['height']}"
    )
    print(f"Detailed CSV saved: {csv_path}")
    print("Alignment:")
    print(f"  ArUco markers: {alignment_info.get('marker_count', 0)} ({', '.join(alignment_info.get('marker_names', []))})")
    print(f"  Mode         : {alignment_info.get('mode', '')}")
    print("Part resolution:")
    print(f"  Filename marker: {filename_part_info.get('status', '')}")
    print(f"  Resolved part  : {resolved_part or 'not resolved'}")
    print("Optional readers:")
    print(f"  Part detector: {'enabled' if enable_part_detector else 'disabled'}")
    print(f"  QR reader    : {'enabled' if enable_qr_reader else 'disabled'}")
    print(f"  Timestamp    : {'enabled' if add_timestamp else 'disabled'}")
    if enable_qr_reader:
        print(f"  QR status    : {qr_info.get('status', '')}")
        print(f"  QR text      : {qr_info.get('text', '')}")
    if enable_part_detector:
        print(f"  Printout part: {printed_part_info.get('part') or ''}")
        print(f"  Part status  : {printed_part_info.get('status', '')}")

    print("Detection metrics:")
    print(f"  Total cells: {metrics['total_cells']}")
    print(f"  Detected T : {metrics['detected_T']}")
    print(f"  Detected F : {metrics['detected_F']}")
    print(f"  Empty      : {metrics['empty']}")
    print(f"  Ambiguous  : {metrics['ambiguous']}")

    if answer_key:
        print("Grading metrics:")
        print(f"  Part       : {resolved_part or 'not resolved'}")
        print(f"  Correct    : {grade_metrics['correct']}")
        print(f"  Incorrect  : {grade_metrics['incorrect']}")
        print(
            f"  Score      : {format_score(grade_metrics['score'])} / "
            f"{format_score(grade_metrics['max_score'])}"
        )
        print(f"  Score map  : {normalize_score_map(score_map)}")

    return (
        detected_rows,
        metrics,
        qr_info,
        graded_rows,
        grade_metrics,
        resolved_part,
        printed_part_info,
        alignment_info,
    )


def detect_marked_values_from_pdf(
    scanned_pdf_path,
    rendered_png_path=RENDERED_PNG,
    vis_path=VIS_PNG,
    csv_path=CSV_PATH,
    answer_key=None,
    part="auto",
    score_map=None,
    enable_part_detector=ENABLE_PART_DETECTOR,
    enable_qr_reader=ENABLE_QR_READER,
    add_timestamp=ADD_TIMESTAMP_TO_DETECTED,
    grader_text=GRADER_HEADER_TEXT,
    min_aruco_markers=MIN_ARUCO_MARKERS,
    detected_scale=DETECTED_OUTPUT_SCALE,
    jpeg_quality=DETECTED_JPEG_QUALITY,
    webp_quality=DETECTED_WEBP_QUALITY,
    png_compression=DETECTED_PNG_COMPRESSION,
):
    pdf_to_png(scanned_pdf_path, rendered_png_path, DPI)
    image = cv2.imread(rendered_png_path)
    if image is None:
        raise FileNotFoundError(rendered_png_path)

    return _run_detection_on_image(
        image=image,
        vis_path=vis_path,
        csv_path=csv_path,
        rendered_png_path=rendered_png_path,
        answer_key=answer_key,
        part=part,
        source_name=scanned_pdf_path,
        page_number=1,
        score_map=score_map,
        enable_part_detector=enable_part_detector,
        enable_qr_reader=enable_qr_reader,
        add_timestamp=add_timestamp,
        grader_text=grader_text,
        min_aruco_markers=min_aruco_markers,
        detected_scale=detected_scale,
        jpeg_quality=jpeg_quality,
        webp_quality=webp_quality,
        png_compression=png_compression,
    )


def detect_marked_values_from_image(
    image_path,
    vis_path=VIS_PNG,
    csv_path=CSV_PATH,
    answer_key=None,
    part="auto",
    score_map=None,
    enable_part_detector=ENABLE_PART_DETECTOR,
    enable_qr_reader=ENABLE_QR_READER,
    add_timestamp=ADD_TIMESTAMP_TO_DETECTED,
    grader_text=GRADER_HEADER_TEXT,
    min_aruco_markers=MIN_ARUCO_MARKERS,
    detected_scale=DETECTED_OUTPUT_SCALE,
    jpeg_quality=DETECTED_JPEG_QUALITY,
    webp_quality=DETECTED_WEBP_QUALITY,
    png_compression=DETECTED_PNG_COMPRESSION,
):
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(image_path)

    return _run_detection_on_image(
        image=image,
        vis_path=vis_path,
        csv_path=csv_path,
        rendered_png_path=None,
        answer_key=answer_key,
        part=part,
        source_name=image_path,
        page_number=1,
        score_map=score_map,
        enable_part_detector=enable_part_detector,
        enable_qr_reader=enable_qr_reader,
        add_timestamp=add_timestamp,
        grader_text=grader_text,
        min_aruco_markers=min_aruco_markers,
        detected_scale=detected_scale,
        jpeg_quality=jpeg_quality,
        webp_quality=webp_quality,
        png_compression=png_compression,
    )
