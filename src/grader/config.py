"""Shared configuration constants for the grader."""

from reportlab.lib.pagesizes import A4
import cv2

NUM_QUESTIONS = 50

STATEMENTS_PER_QUESTION = 4

COLUMNS = 5

PDF_W_PT, PDF_H_PT = A4

MM = 72.0 / 25.4

MARGIN_X_PT = 36

MARGIN_Y_PT = 36

ARUCO_SIZE_PT = 36

QR_RESERVED_W_PT = 30 * MM

QR_RESERVED_H_PT = 30 * MM

QR_RESERVED_EXTRA_CLEARANCE_PT = 6 * MM

STICKER_W_PT = 30.5 * MM

STICKER_H_PT = 20.5 * MM

STICKER_CORNER_LEN_PT = 4 * MM

STICKER_CORNER_RADIUS_PT = 2.0 * MM

ANSWER_CIRCLE_DIAMETER_PT = 4 * MM

QUESTION_NUM_OUTSIDE_GAP_PT = 2.0 * MM

ROW_LABEL_X_OFFSET_PT = 1 * MM

ANSWER_GRID_LEFT_OFFSET_PT = 6 * MM

ANSWER_GRID_RIGHT_OFFSET_PT = 27 * MM

STATEMENT_LABEL_Y_OFFSET_PT = 17.5 * MM

T_ROW_Y_OFFSET_PT = 14 * MM

F_ROW_Y_OFFSET_PT = 6 * MM

QUESTION_AREA_MARGIN_X_PT = 12 * MM

BOTTOM_QUESTION_CLEARANCE_PT = MARGIN_Y_PT + ARUCO_SIZE_PT + 6 * MM

TOP_QUESTION_CLEARANCE_PT = MARGIN_Y_PT + QR_RESERVED_H_PT + QR_RESERVED_EXTRA_CLEARANCE_PT

EMPTY_TEMPLATE_PDF = "omr_empty_template_sticker_circles_fixed_rounded_tighter.pdf"

EMPTY_TEMPLATE_PART_A_PDF = "omr_empty_template_theory_part_a.pdf"

EMPTY_TEMPLATE_PART_B_PDF = "omr_empty_template_theory_part_b.pdf"

MOCK_PDF = "omr_mock_filled_sticker_circles_fixed_rounded_tighter.pdf"

SCANNED_PDF = "scanned_sheet.pdf"

RENDERED_PNG = "sheet_rendered.png"

VIS_PNG = "sheet_detected.jpg"

CSV_PATH = "sheet_detected.csv"

GRADED_CSV_PATH = "sheet_graded.csv"

BULK_INPUT_FOLDER = "scanned_sheets"

BULK_OUTPUT_FOLDER = "bulk_detected"

BULK_METRICS_CSV_NAME = "grader_metrics_all_files.csv"

DPI = 300

DETECTED_OUTPUT_FORMAT = "jpg"

DETECTED_OUTPUT_SCALE = 0.75

DETECTED_JPEG_QUALITY = 82

DETECTED_WEBP_QUALITY = 82

DETECTED_PNG_COMPRESSION = 9

KEEP_RENDERED_IMAGES = False

MIN_ARUCO_MARKERS = 2

ARUCO_RANSAC_REPROJ_THRESHOLD_PX = 5.0

MIN_FILL_DIFF = 0.3

MIN_FILL_FRACTION = 0.3

DARK_PIXEL_THRESHOLD = 110

USE_FIXED_DARK_THRESHOLD = True

ARUCO_DICT_NAME = cv2.aruco.DICT_4X4_50

ARUCO_IDS = {
    "TL": 10,
    "TR": 11,
    "BR": 12,
    "BL": 13,
}

IBO_GREEN_HEX = "#5AAB55"

IBO_RED_HEX = "#D24D3B"

IBO_BLUE_HEX = "#408DC4"

IBO_YELLOW_HEX = "#E8BC05"

IBO_PURPLE_HEX = "#844E94"

IBO_GREY_HEX = "#565759"

IBO_GREEN_BGR = (85, 171, 90)

IBO_RED_BGR = (59, 77, 210)

IBO_BLUE_BGR = (196, 141, 64)

IBO_YELLOW_BGR = (5, 188, 232)

IBO_PURPLE_BGR = (148, 78, 132)

IBO_GREY_BGR = (89, 87, 86)

PART_TITLE_FONT_NAME = "Helvetica-Bold"

PART_TITLE_PREFIX_FONT_SIZE_PT = 20

PART_TITLE_PART_FONT_SIZE_PT = 30

PART_TITLE_FONT_SIZE_PT = PART_TITLE_PREFIX_FONT_SIZE_PT

PART_TITLE_X_PT = MARGIN_X_PT + ARUCO_SIZE_PT + 8

PART_TITLE_BASELINE_Y_PT = (PDF_H_PT - MARGIN_Y_PT - ARUCO_SIZE_PT) + ARUCO_SIZE_PT / 2 - 5 - 2 * MM

PART_TITLE_CROP_X0_PT = MARGIN_X_PT + ARUCO_SIZE_PT + 2 * MM

PART_TITLE_CROP_X1_PT = PDF_W_PT / 2 - QR_RESERVED_W_PT / 2 - 4 * MM

PART_TITLE_CROP_Y0_PT = PDF_H_PT - MARGIN_Y_PT - ARUCO_SIZE_PT - 6 * MM

PART_TITLE_CROP_Y1_PT = PDF_H_PT - MARGIN_Y_PT + 6 * MM

PRINTED_PART_LABELS = {
    "A": "Theory Part A",
    "B": "Theory Part B",
}

PRINTED_PART_MIN_DARK_PIXELS = 40

PRINTED_PART_MIN_CONFIDENCE = 0.035

_PRINTED_PART_REF_CACHE = {}

SCORE_BY_CORRECT_COUNT = {
    0: 0.0,
    1: 0.2,
    2: 0.4,
    3: 0.6,
    4: 1.0,
}

ENABLE_PART_DETECTOR = True

ENABLE_QR_READER = True

ADD_TIMESTAMP_TO_DETECTED = False

GRADER_HEADER_TEXT = "IBO 2026 grader v1.0"

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S %Z"

ALL_FILES_METRICS_FIELDS = [
    "SourceRelativePath",
    "SourcePDF",
    "Page",
    "Status",
    "Error",
    "OutputRelativeFolder",
    "FilenamePart",
    "FilenamePartStatus",
    "PartResolutionSource",
    "ResolvedPart",
    "QRText",
    "QRStatus",
    "PrintoutPart",
    "PrintoutPartStatus",
    "PrintoutPartConfidence",
    "ArUcoMarkersDetected",
    "ArUcoMarkerNames",
    "ArUcoMissingMarkers",
    "AlignmentMode",
    "TotalCells",
    "DetectedTrue",
    "DetectedFalse",
    "DetectedResponses",
    "EmptyIncludingAmbiguous",
    "StrictEmpty",
    "Ambiguous",
    "GradableCells",
    "Correct",
    "Incorrect",
    "Missing",
    "LinearCorrectCells",
    "QuestionsScored",
    "Score",
    "MaxScore",
    "AccuracyPercent",
    "ScorePercent",
    "DetectedFile",
    "DetectedFileSizeBytes",
    "DetectedFileSizeMiB",
    "DetailedCSV",
]
