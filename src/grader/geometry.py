"""Page geometry and PDF/image coordinate conversion."""

import math
import numpy as np

from .config import *


def pdf_to_img_xy(x_pt, y_pt, img_w, img_h):
    sx = img_w / PDF_W_PT
    sy = img_h / PDF_H_PT
    x = x_pt * sx
    y = img_h - (y_pt * sy)
    return np.array([x, y], dtype=np.float32)


def pdf_len_to_px(length_pt, img_w, img_h):
    sx = img_w / PDF_W_PT
    sy = img_h / PDF_H_PT
    return length_pt * (sx + sy) / 2.0


def get_layout_pt():
    questions_per_column = math.ceil(NUM_QUESTIONS / COLUMNS)

    available_w_pt = PDF_W_PT - 2 * QUESTION_AREA_MARGIN_X_PT
    if COLUMNS == 1:
        column_pitch_pt = 0
    else:
        column_pitch_pt = (available_w_pt - STICKER_W_PT) / (COLUMNS - 1)

    available_h_pt = PDF_H_PT - TOP_QUESTION_CLEARANCE_PT - BOTTOM_QUESTION_CLEARANCE_PT
    if questions_per_column == 1:
        row_pitch_pt = 0
    else:
        row_pitch_pt = (available_h_pt - STICKER_H_PT) / (questions_per_column - 1)

    if column_pitch_pt < STICKER_W_PT:
        print(
            "Warning: sticker columns overlap. Increase page width, reduce columns, "
            "or shrink STICKER_W_PT."
        )
    if row_pitch_pt < STICKER_H_PT:
        print(
            "Warning: sticker rows overlap. Increase page height, increase columns, "
            "or shrink STICKER_H_PT."
        )

    return {
        "questions_per_column": questions_per_column,
        "x_start_left_pt": QUESTION_AREA_MARGIN_X_PT,
        "column_pitch_pt": column_pitch_pt,
        "y_start_bottom_pt": BOTTOM_QUESTION_CLEARANCE_PT,
        "row_pitch_pt": row_pitch_pt,
        "available_h_pt": available_h_pt,
        "available_w_pt": available_w_pt,
    }


def question_sticker_rect_pt(col, row_from_top):
    layout = get_layout_pt()
    rows = layout["questions_per_column"]
    x = layout["x_start_left_pt"] + col * layout["column_pitch_pt"]
    y = layout["y_start_bottom_pt"] + (rows - 1 - row_from_top) * layout["row_pitch_pt"]
    return x, y, STICKER_W_PT, STICKER_H_PT


def answer_square_centers_pt(sticker_x, sticker_y):
    if STATEMENTS_PER_QUESTION == 1:
        x_positions = [sticker_x + (ANSWER_GRID_LEFT_OFFSET_PT + ANSWER_GRID_RIGHT_OFFSET_PT) / 2]
    else:
        start = sticker_x + ANSWER_GRID_LEFT_OFFSET_PT
        end = sticker_x + ANSWER_GRID_RIGHT_OFFSET_PT
        step = (end - start) / (STATEMENTS_PER_QUESTION - 1)
        x_positions = [start + s * step for s in range(STATEMENTS_PER_QUESTION)]

    y_t = sticker_y + T_ROW_Y_OFFSET_PT
    y_f = sticker_y + F_ROW_Y_OFFSET_PT
    return [(x, y_t, y_f) for x in x_positions]


def expected_page_corners(img_w, img_h):
    return np.array([
        [0, 0],
        [img_w - 1, 0],
        [img_w - 1, img_h - 1],
        [0, img_h - 1],
    ], dtype=np.float32)


def square_centers_px(img_w, img_h):
    layout = get_layout_pt()
    centers = []
    q_idx = 0

    for col in range(COLUMNS):
        for q in range(layout["questions_per_column"]):
            if q_idx >= NUM_QUESTIONS:
                break

            x_sticker, y_sticker, _, _ = question_sticker_rect_pt(col, q)
            row = []

            for s, (x_pt, y_t_pt, y_f_pt) in enumerate(answer_square_centers_pt(x_sticker, y_sticker)):
                p_t = pdf_to_img_xy(x_pt, y_t_pt, img_w, img_h)
                p_f = pdf_to_img_xy(x_pt, y_f_pt, img_w, img_h)

                row.append({
                    "statement": s + 1,
                    "x": int(round(p_t[0])),
                    "y_t": int(round(p_t[1])),
                    "y_f": int(round(p_f[1])),
                })

            centers.append(row)
            q_idx += 1

    return centers


def bubble_centers_px(img_w, img_h):
    return square_centers_px(img_w, img_h)
