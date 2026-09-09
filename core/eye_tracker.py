"""
core/eye_tracker.py
--------------------
Pure-function Eye Aspect Ratio (EAR) calculations.

These functions are independent of any GUI or camera code, making them
easy to unit-test in isolation.

The EAR formula is derived from:
    Soukupova & Cech (2016) — Real-Time Eye Blink Detection using Facial Landmarks
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # mediapipe landmark types — only used for type hints
    # pyrefly: ignore [missing-import]
    from mediapipe.framework.formats.landmark_pb2 import NormalizedLandmark


def euclidean(p1: "NormalizedLandmark", p2: "NormalizedLandmark") -> float:
    """Return the 2-D Euclidean distance between two normalised landmarks."""
    return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)


def calculate_ear(landmarks: list) -> float:
    """
    Compute the Eye Aspect Ratio for the *left* eye using MediaPipe indices.

    MediaPipe Face Landmarker uses the canonical 468-point mesh.
    The left eye (from the subject's perspective) uses:
        p1 = 33   (inner corner)
        p4 = 133  (outer corner)
        p2 = 159  (upper lid centre)
        p6 = 145  (lower lid centre)

    EAR = ||p2-p6|| / ||p1-p4||

    Returns 0.0 if the horizontal distance is zero (avoid division by zero).
    """
    p1 = landmarks[33]
    p2 = landmarks[159]
    p4 = landmarks[133]
    p6 = landmarks[145]

    dist_vertical: float = euclidean(p2, p6)
    dist_horizontal: float = euclidean(p1, p4)

    if dist_horizontal == 0.0:
        return 0.0
    return dist_vertical / dist_horizontal


def is_blink(ear: float, threshold: float) -> bool:
    """Return True when the EAR value falls below *threshold* (eye closed)."""
    return ear < threshold


def eye_status_label(ear: float, threshold: float) -> str:
    """Return a human-readable eye status string for display in the UI."""
    return "CLOSED ✦ CLICK" if is_blink(ear, threshold) else "OPEN"
