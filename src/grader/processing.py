"""PDF rendering, recursive discovery, and batch processing."""

import os
import cv2
from pdf2image import convert_from_path

from .config import *
from .detection import _run_detection_on_image
from .reporting import write_all_files_metrics_csv
from .visualization import detected_output_extension


def pdf_to_png(pdf_path, png_path=RENDERED_PNG, dpi=DPI):
    pages = convert_from_path(pdf_path, dpi=dpi)
    if not pages:
        raise RuntimeError("No pages rendered from PDF")
    pages[0].save(png_path, "PNG")
    return png_path


def safe_filename_stem(path):
    """Return the original filename, removing only a final .pdf extension.

    Extensionless input names are preserved completely so an input named
    ``LTU_A-1_001`` produces ``LTU_A-1_001_detected.png`` rather than losing
    part of its original name.
    """
    filename = os.path.basename(path)
    if filename.lower().endswith(".pdf"):
        filename = filename[:-4]
    return filename or "sheet"


def is_pdf_file(path):
    """Return True when a regular file contains a PDF signature.

    Detection is based on file contents rather than the filename extension.
    The PDF header is normally at the start of the file, but checking the
    first 1024 bytes also accepts PDFs with a short leading wrapper/preamble.
    """
    if not os.path.isfile(path):
        return False

    try:
        with open(path, "rb") as f:
            header = f.read(1024)
    except OSError:
        return False

    return b"%PDF-" in header


def pdf_to_png_pages(pdf_path, output_folder, stem=None, dpi=DPI):
    pages = convert_from_path(pdf_path, dpi=dpi)
    if not pages:
        raise RuntimeError(f"No pages rendered from PDF: {pdf_path}")

    os.makedirs(output_folder, exist_ok=True)
    stem = stem or safe_filename_stem(pdf_path)
    rendered_paths = []

    for page_idx, page in enumerate(pages, start=1):
        if len(pages) == 1:
            png_path = os.path.join(output_folder, f"{stem}_rendered.png")
        else:
            png_path = os.path.join(output_folder, f"{stem}_page_{page_idx:03d}_rendered.png")

        page.save(png_path, "PNG")
        rendered_paths.append(png_path)

    return rendered_paths


def _is_path_within(path, possible_parent):
    path = os.path.abspath(path)
    possible_parent = os.path.abspath(possible_parent)
    try:
        return os.path.commonpath([path, possible_parent]) == possible_parent
    except ValueError:
        return False


def discover_recursive_pdf_inputs(folder_path, output_folder):
    """Find PDF-content files recursively and mirror output subdirectories.

    Files are accepted whether they end in .pdf or have no extension, as long
    as their contents contain a valid PDF signature.
    """
    input_root = os.path.abspath(folder_path)
    output_root = os.path.abspath(output_folder)
    entries = []

    for current_root, dirnames, filenames in os.walk(input_root):
        # Prevent a nested output directory from being scanned as input.
        dirnames[:] = sorted(
            [
                name
                for name in dirnames
                if os.path.abspath(os.path.join(current_root, name)) != output_root
            ],
            key=str.lower,
        )

        relative_dir = os.path.relpath(current_root, input_root)
        if relative_dir == ".":
            relative_dir = ""
        mirrored_output_dir = os.path.join(output_root, relative_dir)
        os.makedirs(mirrored_output_dir, exist_ok=True)

        for filename in sorted(filenames, key=str.lower):
            pdf_path = os.path.join(current_root, filename)
            if not is_pdf_file(pdf_path):
                continue
            relative_path = os.path.relpath(pdf_path, input_root)
            entries.append({
                "pdf_path": pdf_path,
                "relative_path": relative_path,
                "output_folder": mirrored_output_dir,
            })

    return entries


def detect_marked_values_from_pdf_file(
    pdf_path,
    output_folder=BULK_OUTPUT_FOLDER,
    answer_key=None,
    part="auto",
    score_map=None,
    enable_part_detector=ENABLE_PART_DETECTOR,
    enable_qr_reader=ENABLE_QR_READER,
    add_timestamp=ADD_TIMESTAMP_TO_DETECTED,
    grader_text=GRADER_HEADER_TEXT,
    relative_source_path=None,
    min_aruco_markers=MIN_ARUCO_MARKERS,
    detected_format=DETECTED_OUTPUT_FORMAT,
    detected_scale=DETECTED_OUTPUT_SCALE,
    jpeg_quality=DETECTED_JPEG_QUALITY,
    webp_quality=DETECTED_WEBP_QUALITY,
    png_compression=DETECTED_PNG_COMPRESSION,
    keep_rendered_images=KEEP_RENDERED_IMAGES,
):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Input file not found: {pdf_path}")
    if not is_pdf_file(pdf_path):
        raise ValueError(
            f"Input file does not contain recognizable PDF data: {pdf_path}"
        )

    os.makedirs(output_folder, exist_ok=True)
    stem = safe_filename_stem(pdf_path)
    rendered_png_paths = pdf_to_png_pages(
        pdf_path,
        output_folder=output_folder,
        stem=stem,
        dpi=DPI,
    )

    results = []
    detected_ext = detected_output_extension(detected_format)

    for page_idx, rendered_png_path in enumerate(rendered_png_paths, start=1):
        suffix = (
            stem
            if len(rendered_png_paths) == 1
            else f"{stem}_page_{page_idx:03d}"
        )
        vis_path = os.path.join(output_folder, f"{suffix}_detected.{detected_ext}")
        csv_path = os.path.join(output_folder, f"{suffix}_detected.csv")

        try:
            image = cv2.imread(rendered_png_path)
            if image is None:
                raise FileNotFoundError(rendered_png_path)

            output = _run_detection_on_image(
                image=image,
                vis_path=vis_path,
                csv_path=csv_path,
                rendered_png_path=rendered_png_path,
                answer_key=answer_key,
                part=part,
                source_name=pdf_path,
                page_number=page_idx,
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
            results.append({
                "source_pdf": pdf_path,
                "relative_source_path": (
                    relative_source_path or os.path.basename(pdf_path)
                ),
                "page": page_idx,
                "status": "ok",
                "error": "",
                "detected_png": vis_path,  # legacy metrics field name
                "detected_file": vis_path,
                "detailed_csv": csv_path,
                "requested_part": part,
                "result": output,
            })
        except Exception as exc:
            print(f"FAILED PAGE: {pdf_path}, page {page_idx}")
            print(f"  Error: {exc}")
            results.append({
                "source_pdf": pdf_path,
                "relative_source_path": (
                    relative_source_path or os.path.basename(pdf_path)
                ),
                "page": page_idx,
                "status": "detect_failed",
                "error": str(exc),
                "detected_png": "",
                "detailed_csv": "",
                "requested_part": part,
                "result": None,
            })
        finally:
            if not keep_rendered_images and os.path.exists(rendered_png_path):
                try:
                    os.remove(rendered_png_path)
                except OSError as cleanup_exc:
                    print(f"Warning: could not remove intermediate {rendered_png_path}: {cleanup_exc}")

    print(f"\nCompleted {len(results)} sheet(s) from: {pdf_path}")
    return results


def detect_marked_values_from_pdf_folder(
    folder_path=BULK_INPUT_FOLDER,
    output_folder=BULK_OUTPUT_FOLDER,
    answer_key=None,
    part="auto",
    score_map=None,
    enable_part_detector=ENABLE_PART_DETECTOR,
    enable_qr_reader=ENABLE_QR_READER,
    add_timestamp=ADD_TIMESTAMP_TO_DETECTED,
    grader_text=GRADER_HEADER_TEXT,
    metrics_csv_name=BULK_METRICS_CSV_NAME,
    min_aruco_markers=MIN_ARUCO_MARKERS,
    detected_format=DETECTED_OUTPUT_FORMAT,
    detected_scale=DETECTED_OUTPUT_SCALE,
    jpeg_quality=DETECTED_JPEG_QUALITY,
    webp_quality=DETECTED_WEBP_QUALITY,
    png_compression=DETECTED_PNG_COMPRESSION,
    keep_rendered_images=KEEP_RENDERED_IMAGES,
):
    if not os.path.isdir(folder_path):
        raise FileNotFoundError(f"Bulk input folder not found: {folder_path}")

    os.makedirs(output_folder, exist_ok=True)
    pdf_entries = discover_recursive_pdf_inputs(folder_path, output_folder)
    metrics_csv_path = os.path.join(output_folder, metrics_csv_name)

    if not pdf_entries:
        print(f"No PDF-content files found recursively in folder: {folder_path}")
        write_all_files_metrics_csv(metrics_csv_path, [], output_folder)
        return []

    all_results = []

    print(f"Bulk input folder : {folder_path}")
    print(f"Bulk output folder: {output_folder}")
    print(f"PDF-content files found recursively: {len(pdf_entries)}")

    for entry in pdf_entries:
        pdf_path = entry["pdf_path"]
        print(f"\n=== Processing: {entry['relative_path']} ===")
        try:
            results = detect_marked_values_from_pdf_file(
                pdf_path=pdf_path,
                output_folder=entry["output_folder"],
                answer_key=answer_key,
                part=part,
                score_map=score_map,
                enable_part_detector=enable_part_detector,
                enable_qr_reader=enable_qr_reader,
                add_timestamp=add_timestamp,
                grader_text=grader_text,
                relative_source_path=entry["relative_path"],
                min_aruco_markers=min_aruco_markers,
                detected_format=detected_format,
                detected_scale=detected_scale,
                jpeg_quality=jpeg_quality,
                webp_quality=webp_quality,
                png_compression=png_compression,
                keep_rendered_images=keep_rendered_images,
            )
            all_results.extend(results)
        except Exception as exc:
            print(f"FAILED TO RENDER: {entry['relative_path']}")
            print(f"  Error: {exc}")
            all_results.append({
                "source_pdf": pdf_path,
                "relative_source_path": entry["relative_path"],
                "page": "",
                "status": "render_failed",
                "error": str(exc),
                "detected_png": "",
                "detailed_csv": "",
                "requested_part": part,
                "result": None,
            })

    write_all_files_metrics_csv(
        metrics_csv_path,
        all_results,
        output_folder,
    )

    print("\nBulk detection complete.")
    print(f"Mirrored per-sheet outputs saved in: {output_folder}")
    print(f"All-files metrics CSV: {metrics_csv_path}")
    return all_results
