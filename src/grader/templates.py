"""Printable template and mock-sheet generation."""

import os
import random
import cv2
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from .config import *
from .geometry import *
from .grading import normalize_part


def aruco_rects_pdf():
    return {
        "TL": {
            "id": ARUCO_IDS["TL"],
            "x": MARGIN_X_PT,
            "y": PDF_H_PT - MARGIN_Y_PT - ARUCO_SIZE_PT,
            "size": ARUCO_SIZE_PT,
        },
        "TR": {
            "id": ARUCO_IDS["TR"],
            "x": PDF_W_PT - MARGIN_X_PT - ARUCO_SIZE_PT,
            "y": PDF_H_PT - MARGIN_Y_PT - ARUCO_SIZE_PT,
            "size": ARUCO_SIZE_PT,
        },
        "BR": {
            "id": ARUCO_IDS["BR"],
            "x": PDF_W_PT - MARGIN_X_PT - ARUCO_SIZE_PT,
            "y": MARGIN_Y_PT,
            "size": ARUCO_SIZE_PT,
        },
        "BL": {
            "id": ARUCO_IDS["BL"],
            "x": MARGIN_X_PT,
            "y": MARGIN_Y_PT,
            "size": ARUCO_SIZE_PT,
        },
    }


def generate_aruco_marker_png(marker_id, px_size):
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_NAME)
    img = np.zeros((px_size, px_size), dtype=np.uint8)
    cv2.aruco.generateImageMarker(aruco_dict, marker_id, px_size, img, 1)
    return img


def draw_aruco_marker_pdf(c, rect, px_size=300):
    marker = generate_aruco_marker_png(rect["id"], px_size)
    tmp_path = f"_aruco_{rect['id']}.png"
    cv2.imwrite(tmp_path, marker)
    c.drawImage(tmp_path, rect["x"], rect["y"], width=rect["size"], height=rect["size"], mask="auto")
    os.remove(tmp_path)


def draw_l_corner_guides(c, x, y, w, h):
    L = STICKER_CORNER_LEN_PT
    r = STICKER_CORNER_RADIUS_PT
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.6)

    def draw_path(items):
        p = c.beginPath()
        p.moveTo(items[0][0], items[0][1])
        for item in items[1:]:
            if len(item) == 2:
                p.lineTo(item[0], item[1])
            else:
                p.curveTo(*item)
        c.drawPath(p, stroke=1, fill=0)

    # Bottom-left
    draw_path([
        (x + L, y),
        (x + r, y),
        (x + r * 0.45, y, x, y + r * 0.45, x, y + r),
        (x, y + L),
    ])
    # Bottom-right
    draw_path([
        (x + w - L, y),
        (x + w - r, y),
        (x + w - r * 0.45, y, x + w, y + r * 0.45, x + w, y + r),
        (x + w, y + L),
    ])
    # Top-left
    draw_path([
        (x + L, y + h),
        (x + r, y + h),
        (x + r * 0.45, y + h, x, y + h - r * 0.45, x, y + h - r),
        (x, y + h - L),
    ])
    # Top-right
    draw_path([
        (x + w - L, y + h),
        (x + w - r, y + h),
        (x + w - r * 0.45, y + h, x + w, y + h - r * 0.45, x + w, y + h - r),
        (x + w, y + h - L),
    ])


def draw_answer_circle(c, x, y, filled=False):
    radius = ANSWER_CIRCLE_DIAMETER_PT / 2.0

    if filled:
        c.setFillColorRGB(0, 0, 0)
        c.circle(x, y, max(0.1, radius - 0.5), fill=1, stroke=0)

    c.setFillColorRGB(1, 1, 1)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.6)
    c.circle(x, y, radius, fill=0, stroke=1)


def _hex_to_rgb01(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def _part_title_color_hex(part):
    part = normalize_part(part)
    if part == "A":
        return IBO_RED_HEX
    if part == "B":
        return IBO_BLUE_HEX
    return IBO_GREY_HEX


def draw_part_title_pdf(c, label_text):
    """Draw arbitrary customizable text in the top-left header."""
    if label_text is None:
        return

    label = str(label_text).strip()

    if not label:
        return

    c.setFillColorRGB(*_hex_to_rgb01(IBO_GREY_HEX))
    c.setFont(PART_TITLE_FONT_NAME, PART_TITLE_FONT_SIZE_PT)
    c.drawString(
        PART_TITLE_X_PT,
        PART_TITLE_BASELINE_Y_PT,
        label,
    )


draw_sheet_header(
    c,
    label_text=label_text,
    logo_path=logo_path,
):
    """Draw optional customizable header text and optional logo."""
    markers = aruco_rects_pdf()
    tr = markers["TR"]

    if label_text:
        draw_part_title_pdf(c, label_text)

    if logo_path:
        if not os.path.exists(logo_path):
            raise FileNotFoundError(
                f"Logo path not found: {logo_path}"
            )

        img = ImageReader(logo_path)
        img_w, img_h = img.getSize()

        max_w = 72
        max_h = 48
        scale = min(max_w / img_w, max_h / img_h)

        draw_w = img_w * scale
        draw_h = img_h * scale

        logo_x = tr["x"] - draw_w - 8 - 3 * MM
        logo_y = tr["y"] + (tr["size"] - draw_h) / 2

        c.drawImage(
            img,
            logo_x,
            logo_y,
            width=draw_w,
            height=draw_h,
            preserveAspectRatio=True,
            mask="auto",
        )



def draw_sheet_page(
    c,
    fill_answers=False,
    seed=1,
    draw_qr_placeholder=False,
    label_text=None,
    logo_path=None,
):
    """Draw one complete answer-sheet page on an existing ReportLab canvas."""
    markers = aruco_rects_pdf()

    for key in ["TL", "TR", "BR", "BL"]:
        draw_aruco_marker_pdf(c, markers[key])

    draw_sheet_header(c, part_title=part_title, logo_path=logo_path)

    # Keep this area clear for a QR code. It is outlined only when requested.
    if draw_qr_placeholder:
        qr_x = (PDF_W_PT - QR_RESERVED_W_PT) / 2
        qr_y = PDF_H_PT - MARGIN_Y_PT - QR_RESERVED_H_PT
        c.setStrokeColorRGB(0.75, 0.75, 0.75)
        c.setDash(2, 2)
        c.rect(qr_x, qr_y, QR_RESERVED_W_PT, QR_RESERVED_H_PT, fill=0, stroke=1)
        c.setDash()

    rng = random.Random(seed)
    answer_key = []
    layout = get_layout_pt()
    q_idx = 0

    for col in range(COLUMNS):
        for q in range(layout["questions_per_column"]):
            if q_idx >= NUM_QUESTIONS:
                break

            x, y, w, h = question_sticker_rect_pt(col, q)
            draw_l_corner_guides(c, x, y, w, h)

            c.setFillColorRGB(0, 0, 0)
            c.setFont("Helvetica-Bold", 8)
            c.drawRightString(
                x - QUESTION_NUM_OUTSIDE_GAP_PT,
                y + h / 2 - 3,
                str(q_idx + 1),
            )

            c.setFont("Helvetica", 5.5)
            c.drawString(x + ROW_LABEL_X_OFFSET_PT, y + T_ROW_Y_OFFSET_PT - 2, "T")
            c.drawString(x + ROW_LABEL_X_OFFSET_PT, y + F_ROW_Y_OFFSET_PT - 2, "F")

            row_answers = []
            centers = answer_square_centers_pt(x, y)

            c.setFont("Helvetica-Bold", 6)
            for s, (x_pt, y_t_pt, y_f_pt) in enumerate(centers):
                c.setFillColorRGB(0, 0, 0)
                c.drawCentredString(
                    x_pt,
                    y + STATEMENT_LABEL_Y_OFFSET_PT,
                    str(s + 1),
                )

                choice = rng.choice(["T", "F"]) if fill_answers else ""
                row_answers.append(choice)

                draw_answer_circle(c, x_pt, y_t_pt, filled=(choice == "T"))
                draw_answer_circle(c, x_pt, y_f_pt, filled=(choice == "F"))

            answer_key.append(row_answers)
            q_idx += 1

    return answer_key


def draw_sheet(
    path,
    fill_answers=False,
    seed=1,
    draw_qr_placeholder=False,
    part_title=None,
    logo_path=None,
):
    """Generate a one-page answer-sheet PDF."""
    c = canvas.Canvas(path, pagesize=A4)
    answer_key = draw_sheet_page(
        c,
        fill_answers=fill_answers,
        seed=seed,
        draw_qr_placeholder=draw_qr_placeholder,
        part_title=part_title,
        logo_path=logo_path,
    )
    c.save()
    return answer_key


def generate_empty_template(path=EMPTY_TEMPLATE_PDF, part_title=None, logo_path=None):
    draw_sheet(path, fill_answers=False, part_title=part_title, logo_path=logo_path)


def generate_part_templates(logo_path=None):
    generate_empty_template(EMPTY_TEMPLATE_PART_A_PDF, part_title="Theory Part A", logo_path=logo_path)
    generate_empty_template(EMPTY_TEMPLATE_PART_B_PDF, part_title="Theory Part B", logo_path=logo_path)
    return EMPTY_TEMPLATE_PART_A_PDF, EMPTY_TEMPLATE_PART_B_PDF


def generate_mock_pdf(path=MOCK_PDF, seed=1, part_title=None, logo_path=None):
    return draw_sheet(path, fill_answers=True, seed=seed, part_title=part_title, logo_path=logo_path)
