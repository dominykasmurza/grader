"""ArUco detection and page alignment."""

import cv2
import numpy as np

from .config import *
from .geometry import pdf_to_img_xy
from .templates import aruco_rects_pdf


def detect_aruco_markers(gray):
    """Detect any recognized sheet ArUco markers.

    Unlike older versions, this does not require all four markers. If duplicate
    detections of the same ID occur, the largest marker candidate is retained.
    """
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_NAME)
    detector_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, detector_params)

    corners, ids, rejected = detector.detectMarkers(gray)
    if ids is None or len(ids) == 0:
        raise Exception("Detected 0 recognized ArUco markers")

    required_ids = set(ARUCO_IDS.values())
    found = {}
    found_area = {}

    for marker_corners, marker_id in zip(corners, ids.flatten()):
        marker_id = int(marker_id)
        if marker_id not in required_ids:
            continue
        pts = marker_corners.reshape(4, 2).astype(np.float32)
        area = abs(float(cv2.contourArea(pts)))
        if marker_id not in found or area > found_area[marker_id]:
            found[marker_id] = pts
            found_area[marker_id] = area

    if not found:
        raise Exception("No required sheet ArUco marker IDs were detected")
    return found


def expected_aruco_corners_px(img_w, img_h):
    rects = aruco_rects_pdf()
    out = {}

    for name, rect in rects.items():
        x = rect["x"]
        y = rect["y"]
        size = rect["size"]

        pts_pdf = [
            (x,        y + size),
            (x + size, y + size),
            (x + size, y),
            (x,        y),
        ]

        out[name] = np.array(
            [pdf_to_img_xy(px, py, img_w, img_h) for px, py in pts_pdf],
            dtype=np.float32,
        )

    return out


def warp_with_markers(image, min_markers=MIN_ARUCO_MARKERS):
    """Straighten a sheet using the best transform supported by detected markers.

    4 or 3 markers: perspective homography.
    2 markers: full affine transform.
    1 marker: similarity transform, only when min_markers <= 1.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    found = detect_aruco_markers(gray)

    img_h, img_w = image.shape[:2]
    expected = expected_aruco_corners_px(img_w, img_h)
    marker_order = ["TL", "TR", "BR", "BL"]
    detected_names = [name for name in marker_order if ARUCO_IDS[name] in found]
    marker_count = len(detected_names)

    min_markers = int(min_markers)
    if min_markers < 1 or min_markers > 4:
        raise ValueError(f"min_markers must be 1..4, got {min_markers}")
    if marker_count < min_markers:
        raise Exception(
            f"Detected {marker_count} required ArUco marker(s), need at least {min_markers}. "
            f"Detected: {detected_names or 'none'}"
        )

    src = np.concatenate(
        [found[ARUCO_IDS[name]] for name in detected_names], axis=0
    ).astype(np.float32)
    dst = np.concatenate(
        [expected[name] for name in detected_names], axis=0
    ).astype(np.float32)

    transform_mode = ""
    if marker_count >= 3:
        H, inlier_mask = cv2.findHomography(
            src,
            dst,
            method=cv2.RANSAC,
            ransacReprojThreshold=ARUCO_RANSAC_REPROJ_THRESHOLD_PX,
        )
        if H is None:
            H, inlier_mask = cv2.findHomography(src, dst, method=0)
        if H is None:
            raise Exception(f"Could not estimate homography from {marker_count} markers")
        warped = cv2.warpPerspective(image, H, (img_w, img_h))
        transform_mode = f"homography_{marker_count}_markers"

    elif marker_count == 2:
        M, inlier_mask = cv2.estimateAffine2D(
            src,
            dst,
            method=cv2.RANSAC,
            ransacReprojThreshold=ARUCO_RANSAC_REPROJ_THRESHOLD_PX,
            maxIters=3000,
            confidence=0.995,
            refineIters=20,
        )
        if M is None:
            M, inlier_mask = cv2.estimateAffinePartial2D(
                src,
                dst,
                method=cv2.RANSAC,
                ransacReprojThreshold=ARUCO_RANSAC_REPROJ_THRESHOLD_PX,
                maxIters=3000,
                confidence=0.995,
                refineIters=20,
            )
            transform_mode = "similarity_2_markers"
        else:
            transform_mode = "affine_2_markers"
        if M is None:
            raise Exception("Could not estimate an affine transform from 2 markers")
        warped = cv2.warpAffine(image, M, (img_w, img_h))

    else:  # marker_count == 1, permitted only when min_markers <= 1
        M, inlier_mask = cv2.estimateAffinePartial2D(
            src,
            dst,
            method=cv2.LMEDS,
        )
        if M is None:
            raise Exception("Could not estimate a similarity transform from 1 marker")
        warped = cv2.warpAffine(image, M, (img_w, img_h))
        transform_mode = "similarity_1_marker_low_confidence"

    missing_names = [name for name in marker_order if name not in detected_names]
    alignment_info = {
        "marker_count": marker_count,
        "marker_names": detected_names,
        "marker_ids": [ARUCO_IDS[name] for name in detected_names],
        "missing_marker_names": missing_names,
        "mode": transform_mode,
        "minimum_required": min_markers,
    }
    return warped, src, dst, found, alignment_info
