"""Grader: optical mark recognition for theory examinations."""

__version__ = "1.0.0"

from .grading import (
    grade_detected_rows,
    load_answer_key,
    normalize_answer,
    normalize_part,
    normalize_score_map,
    parse_score_map_arg,
)
from .processing import (
    detect_marked_values_from_pdf_file,
    detect_marked_values_from_pdf_folder,
)

from .qr_sheets import (
    QRSheetRecord,
    generate_qr_answer_sheets,
    generate_qr_answer_sheets_from_csv,
    read_qr_sheet_csv,
)
