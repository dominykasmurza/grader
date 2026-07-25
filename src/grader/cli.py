"""Command-line interface."""

import argparse
import os

from . import config
from .config import *
from .grading import answer_key_part_labels, load_answer_key, parse_score_map_arg
from .processing import (
    detect_marked_values_from_pdf_file,
    detect_marked_values_from_pdf_folder,
)
from .reporting import write_all_files_metrics_csv
from .templates import (
    generate_empty_template,
    generate_mock_pdf,
)


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Generate OMR templates and detect/grade scanned IBO answer sheets."
    )
    parser.add_argument(
        "input_path",
        nargs="?",
        help=(
            "PDF-content file or folder of PDF-content files. The .pdf extension "
            "is optional. If omitted, uses scanned_sheets/ if present, then "
            "scanned_sheet.pdf."
        ),
    )
    parser.add_argument(
        "--output-folder",
        default=BULK_OUTPUT_FOLDER,
        help=(
            "Output folder for compact detected files and one detailed "
            f"CSV per sheet. Default: {BULK_OUTPUT_FOLDER}"
        ),
    )
    parser.add_argument(
        "--detected-format",
        default=DETECTED_OUTPUT_FORMAT,
        choices=["jpg", "png", "webp"],
        help=(
            "Format for annotated _detected files. JPEG is the smallest and is "
            f"the default ({DETECTED_OUTPUT_FORMAT})."
        ),
    )
    parser.add_argument(
        "--detected-scale",
        type=float,
        default=DETECTED_OUTPUT_SCALE,
        help=(
            "Scale applied only to the saved annotated file, not to detection. "
            f"Default: {DETECTED_OUTPUT_SCALE}"
        ),
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=DETECTED_JPEG_QUALITY,
        help=f"JPEG quality 1..100. Default: {DETECTED_JPEG_QUALITY}",
    )
    parser.add_argument(
        "--webp-quality",
        type=int,
        default=DETECTED_WEBP_QUALITY,
        help=f"WebP quality 1..100. Default: {DETECTED_WEBP_QUALITY}",
    )
    parser.add_argument(
        "--png-compression",
        type=int,
        default=DETECTED_PNG_COMPRESSION,
        help=f"PNG compression 0..9. Default: {DETECTED_PNG_COMPRESSION}",
    )
    parser.add_argument(
        "--keep-rendered-images",
        action="store_true",
        help="Keep the large temporary _rendered.png files. They are deleted by default.",
    )
    parser.add_argument(
        "--min-aruco-markers",
        type=int,
        choices=[1, 2, 3, 4],
        default=MIN_ARUCO_MARKERS,
        help=(
            "Minimum recognized ArUco markers required. Default is 2. Set to 1 "
            "only as a last-resort because whole-page alignment is less reliable."
        ),
    )
    parser.add_argument(
        "--answer-key",
        default=None,
        help=(
            "Path to .xlsx answer key. Column A contains the question number/code, "
            "column B contains the PartLabel for every question, and columns D-G "
            "contain the four correct T/F answers."
        ),
    )
    parser.add_argument(
        "--part",
        default="auto",
        metavar="LABEL|auto",
        help=(
            "Answer-key PartLabel used for grading. An explicit label must match "
            "a PartLabel in the answer key. With auto, configured labels are "
            "matched in the filename and QR payload; both must agree when present."
        ),
    )
    parser.add_argument(
        "--read-title-text",
        action="store_true",
        help=(
            "Use OCR to read the customizable top-left sheet title and write it "
            "to the detailed and all-files CSV reports. The title is never used "
            "to resolve Part A/B."
        ),
    )
    parser.add_argument(
        "--title-ocr-language",
        default=TITLE_OCR_LANGUAGE,
        help=(
            "Tesseract language code for --read-title-text. "
            f"Default: {TITLE_OCR_LANGUAGE}"
        ),
    )
    parser.add_argument(
        "--disable-qr-reader",
        action="store_true",
        help="Disable QR-code detection, decoding, and QR debug drawing.",
    )
    parser.add_argument(
        "--timestamp",
        action="store_true",
        help="Print the local date/time and timezone on each _detected file.",
    )
    parser.add_argument(
        "--grader-label",
        default=GRADER_HEADER_TEXT,
        help=f'Text printed at the top of detected files. Default: "{GRADER_HEADER_TEXT}"',
    )
    parser.add_argument(
        "--metrics-csv-name",
        default=BULK_METRICS_CSV_NAME,
        help=(
            "Filename for the all-files metrics CSV written at the root of the "
            f"output folder. Default: {BULK_METRICS_CSV_NAME}"
        ),
    )
    parser.add_argument(
        "--score-map",
        default="0:0,1:0.2,2:0.4,3:0.6,4:1.0",
        help=(
            "Nonlinear per-question score map by number of correct statements. "
            "Default: 0:0,1:0.2,2:0.4,3:0.6,4:1.0"
        ),
    )
    parser.add_argument(
        "--logo-path",
        default=None,
        help=(
            "Path to logo image to place next to the top-right ArUco marker "
            "in generated templates."
        ),
    )
    parser.add_argument(
        "--skip-template-generation",
        action="store_true",
        help="Do not generate empty templates/mock sheet before detection.",
    )
    parser.add_argument(
        "--template-only",
        action="store_true",
        help="Only generate templates, then exit.",
    )
    parser.add_argument(
        "--skip-mock-generation",
        action="store_true",
        help="Do not generate the mock filled sheet.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=DPI,
        help=f"PDF rendering DPI. Default: {DPI}",
    )
    parser.add_argument(
        "--template-label",
        default=None,
        help=(
            "Optional text printed in the top-left of generated "
            "template.pdf and template_filled.pdf. "
            "By default, no label is printed."
        ),
    )

    return parser


def main():
    args = build_arg_parser().parse_args()
    config.DPI = args.dpi
    from . import processing
    processing.DPI = args.dpi

    answer_key = load_answer_key(args.answer_key) if args.answer_key else {}
    score_map = parse_score_map_arg(args.score_map)

    enable_title_ocr = ENABLE_TITLE_OCR or args.read_title_text
    enable_qr_reader = ENABLE_QR_READER and not args.disable_qr_reader
    add_timestamp = ADD_TIMESTAMP_TO_DETECTED or args.timestamp

    print(f"Score map: {score_map}")
    print(f"Title OCR: {'enabled' if enable_title_ocr else 'disabled'}")
    print(f"QR reader: {'enabled' if enable_qr_reader else 'disabled'}")
    print(f"Timestamp: {'enabled' if add_timestamp else 'disabled'}")
    print(f"Detected output: {args.detected_format}, scale={args.detected_scale}")
    print(f"Keep rendered intermediates: {'yes' if args.keep_rendered_images else 'no'}")
    print(f"Minimum ArUco markers: {args.min_aruco_markers}")

    if answer_key:
        part_labels = answer_key_part_labels(answer_key)
        print(
            f"Answer key loaded: {args.answer_key} "
            f"({len(answer_key)} questions)"
        )
        print(f"Answer-key part labels: {', '.join(part_labels)}")

    if not args.skip_template_generation:
        generate_empty_template(
            path=EMPTY_TEMPLATE_PDF,
            label_text=args.template_label,
            logo_path=args.logo_path,
        )
        print(f"Empty template saved: {EMPTY_TEMPLATE_PDF}")

        if not args.skip_mock_generation:
            generate_mock_pdf(
                path=MOCK_PDF,
                seed=1,
                label_text=args.template_label,
                logo_path=args.logo_path,
            )
            print(f"Mock filled sheet saved: {MOCK_PDF}")

    if args.template_only:
        return

    input_path = args.input_path

    if input_path is None:
        if os.path.isdir(BULK_INPUT_FOLDER):
            input_path = BULK_INPUT_FOLDER
        elif os.path.exists(SCANNED_PDF):
            input_path = SCANNED_PDF
        else:
            print(
                f"No input supplied, no bulk folder found at: "
                f"{BULK_INPUT_FOLDER}"
            )
            print(f"No scanned PDF found at: {SCANNED_PDF}")
            return

    common_kwargs = {
        "output_folder": args.output_folder,
        "answer_key": answer_key,
        "part": args.part,
        "score_map": score_map,
        "enable_title_ocr": enable_title_ocr,
        "title_ocr_language": args.title_ocr_language,
        "enable_qr_reader": enable_qr_reader,
        "add_timestamp": add_timestamp,
        "grader_text": args.grader_label,
        "min_aruco_markers": args.min_aruco_markers,
        "detected_format": args.detected_format,
        "detected_scale": args.detected_scale,
        "jpeg_quality": args.jpeg_quality,
        "webp_quality": args.webp_quality,
        "png_compression": args.png_compression,
        "keep_rendered_images": args.keep_rendered_images,
    }

    if os.path.isdir(input_path):
        detect_marked_values_from_pdf_folder(
            folder_path=input_path,
            metrics_csv_name=args.metrics_csv_name,
            **common_kwargs,
        )

    elif os.path.isfile(input_path):
        results = detect_marked_values_from_pdf_file(
            pdf_path=input_path,
            **common_kwargs,
        )

        write_all_files_metrics_csv(
            os.path.join(
                args.output_folder,
                args.metrics_csv_name,
            ),
            results,
            args.output_folder,
        )

    else:
        raise FileNotFoundError(
            f"Input path not found: {input_path}"
        )


if __name__ == "__main__":
    main()
