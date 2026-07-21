"""Answer-key loading and configurable question scoring."""

import os
import re

from .config import *


def normalize_score_map(score_map=None):
    """Return a complete score map for 0..STATEMENTS_PER_QUESTION correct answers."""
    merged = dict(SCORE_BY_CORRECT_COUNT)
    if score_map:
        for key, value in score_map.items():
            merged[int(key)] = float(value)

    normalized = {}
    for i in range(STATEMENTS_PER_QUESTION + 1):
        normalized[i] = float(merged.get(i, 0.0))
    return normalized


def parse_score_map_arg(text):
    """Parse CLI score map, e.g. '0:0,1:0.2,2:0.4,3:0.6,4:1'."""
    if text is None or str(text).strip() == "":
        return normalize_score_map()

    parsed = {}
    for chunk in str(text).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            raise ValueError(f"Invalid score map item: {chunk}. Expected format like 2:0.4")
        key_text, value_text = chunk.split(":", 1)
        key = int(key_text.strip())
        value = float(value_text.strip())
        if key < 0 or key > STATEMENTS_PER_QUESTION:
            raise ValueError(f"Score map key must be 0..{STATEMENTS_PER_QUESTION}, got {key}")
        parsed[key] = value

    return normalize_score_map(parsed)


def format_score(value):
    """Compact score formatting for overlays and CSV-friendly console output."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return ""
    text = f"{value:.2f}"
    text = text.rstrip("0").rstrip(".")
    return text if text else "0"


def normalize_answer(value):
    if value is None:
        return ""
    text = str(value).strip().upper()
    if text in {"TRUE", "T", "1"}:
        return "T"
    if text in {"FALSE", "F", "0"}:
        return "F"
    return ""


def normalize_part(part):
    if part is None:
        return None
    text = str(part).strip().upper()
    if text in {"A", "PART A", "THEORY PART A", "THEORY_A", "THEORY-PART-A"}:
        return "A"
    if text in {"B", "PART B", "THEORY PART B", "THEORY_B", "THEORY-PART-B"}:
        return "B"
    return None


def load_answer_key(answer_key_path):
    """Read question code from column A and correct answers from columns D-G.

    Expected rows look like: A01 ... D-G contain T/F. Header rows are ignored.
    Returns dict like {"A01": ["T", "F", "T", "T"], "B50": [...]}.
    """
    if not answer_key_path:
        return {}
    if not os.path.exists(answer_key_path):
        raise FileNotFoundError(f"Answer key not found: {answer_key_path}")

    try:
        from openpyxl import load_workbook
    except ImportError as e:
        raise ImportError("Reading .xlsx answer keys requires openpyxl: pip install openpyxl") from e

    wb = load_workbook(answer_key_path, data_only=True, read_only=True)
    ws = wb.active

    answer_key = {}
    for row in ws.iter_rows(min_row=1, values_only=True):
        code = row[0] if len(row) > 0 else None
        code = str(code).strip().upper() if code is not None else ""
        if not re.fullmatch(r"[AB]\d{1,2}", code):
            continue
        code = f"{code[0]}{int(code[1:]):02d}"
        answers = [normalize_answer(row[i] if len(row) > i else None) for i in range(3, 7)]
        if len(answers) == STATEMENTS_PER_QUESTION and all(a in {"T", "F"} for a in answers):
            answer_key[code] = answers

    return answer_key


def question_code_for(part, question_number):
    part = normalize_part(part)
    if not part:
        return ""
    return f"{part}{int(question_number):02d}"


def grade_detected_rows(detected_rows, answer_key, part, score_map=None):
    score_map = normalize_score_map(score_map)
    default_max_question_score = score_map.get(
        STATEMENTS_PER_QUESTION,
        max(score_map.values()) if score_map else float(STATEMENTS_PER_QUESTION),
    )

    graded_rows = []
    metrics = {
        "gradable_cells": 0,
        "correct": 0,
        "incorrect": 0,
        "missing": 0,
        "ambiguous": 0,
        "score": 0.0,
        "max_score": 0.0,
        "linear_correct_cells": 0,
        "question_count": 0,
        "score_map": score_map,
    }

    for q_idx, row in enumerate(detected_rows, start=1):
        code = question_code_for(part, q_idx)
        correct = answer_key.get(code, [""] * STATEMENTS_PER_QUESTION)
        result = []
        correct_count = 0
        gradable_count = 0

        for s_idx, detected in enumerate(row):
            correct_answer = correct[s_idx] if s_idx < len(correct) else ""
            if correct_answer in {"T", "F"}:
                metrics["gradable_cells"] += 1
                gradable_count += 1

                if detected == correct_answer:
                    result.append("correct")
                    metrics["correct"] += 1
                    metrics["linear_correct_cells"] += 1
                    correct_count += 1
                elif detected in {"T", "F"}:
                    result.append("incorrect")
                    metrics["incorrect"] += 1
                else:
                    result.append("missing")
                    metrics["missing"] += 1
            else:
                result.append("no_key")

        # Nonlinear question-level scoring. With the default map:
        # 0 correct = 0, 1 = 0.2, 2 = 0.4, 3 = 0.6, 4 = 1.0.
        row_score = float(score_map.get(correct_count, 0.0))
        row_max = float(score_map.get(gradable_count, default_max_question_score)) if gradable_count else 0.0

        metrics["score"] += row_score
        metrics["max_score"] += row_max
        if gradable_count:
            metrics["question_count"] += 1

        graded_rows.append({
            "question": q_idx,
            "code": code,
            "detected": row,
            "correct": correct,
            "result": result,
            "correct_count": correct_count,
            "gradable_count": gradable_count,
            "score": row_score,
            "max_score": row_max,
        })

    return graded_rows, metrics
