"""
core/camera.py
--------------
Camera management and MediaPipe model download.

Responsibilities:
  - Enumerate available cameras
  - Open / release the capture device
  - Read frames safely
  - Download the face_landmarker.task model with progress reporting
"""

from __future__ import annotations

import os
import urllib.request
from typing import Callable, Optional

import cv2

from utils.logger import get_logger
from utils.resource import resource_path

log = get_logger(__name__)

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

MODEL_RELATIVE_PATH = os.path.join("models", "face_landmarker.task")


def get_model_path() -> str:
    """Return the absolute path to face_landmarker.task."""
    return resource_path(MODEL_RELATIVE_PATH)


def is_model_available() -> bool:
    """Return True if the model file exists on disk."""
    return os.path.exists(get_model_path())


def download_model(
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> bool:
    """
    Download face_landmarker.task to the models/ directory.

    Parameters
    ----------
    progress_callback:
        Called with (bytes_downloaded, total_bytes) during download.
        May be called with total_bytes == 0 if Content-Length is absent.

    Returns True on success, False on failure.
    """
    dest = get_model_path()
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    log.info("Downloading model from %s → %s", MODEL_URL, dest)

    try:
        def _reporthook(block_num: int, block_size: int, total_size: int) -> None:
            downloaded = block_num * block_size
            if progress_callback:
                progress_callback(downloaded, total_size)

        urllib.request.urlretrieve(MODEL_URL, dest, reporthook=_reporthook)
        log.info("Model downloaded successfully")
        return True
    except Exception as exc:
        log.error("Model download failed: %s", exc)
        # Remove partial file
        if os.path.exists(dest):
            try:
                os.remove(dest)
            except OSError:
                pass
        return False


class CameraManager:
    """
    Thin wrapper around cv2.VideoCapture.

    Opens a camera by index, reads frames, and releases the device cleanly.
    """

    def __init__(self) -> None:
        self._cap: Optional[cv2.VideoCapture] = None
        self._index: int = 0

    # ── public API ──────────────────────────────────────────────

    @staticmethod
    def list_cameras(max_probe: int = 6) -> list[int]:
        """
        Return a list of camera indices that successfully open.

        Probes indices 0 … max_probe-1.
        """
        available: list[int] = []
        for i in range(max_probe):
            cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if cap.isOpened():
                available.append(i)
                cap.release()
        log.info("Available cameras: %s", available)
        return available

    def open(self, index: int = 0, width: int = 640, height: int = 480) -> bool:
        """
        Open the camera at *index*.

        Returns True on success. On failure, logs a warning and returns False.
        """
        self.release()
        self._index = index
        try:
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                log.warning("Camera %d could not be opened", index)
                return False
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self._cap = cap
            log.info(
                "Camera %d opened at %dx%d",
                index,
                int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )
            return True
        except Exception as exc:
            log.error("Exception opening camera %d: %s", index, exc)
            return False

    def read_frame(self) -> tuple[bool, Optional[object]]:
        """
        Read one frame from the camera.

        Returns (True, frame) on success, (False, None) on failure.
        """
        if self._cap is None or not self._cap.isOpened():
            return False, None
        success, frame = self._cap.read()
        if not success:
            log.warning("Camera %d: failed to read frame", self._index)
        return success, frame if success else None

    def release(self) -> None:
        """Release the VideoCapture device."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            log.info("Camera %d released", self._index)

    @property
    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def current_index(self) -> int:
        return self._index

    def set_resolution(self, width: int, height: int) -> bool:
        """Dynamically adjust camera resolution."""
        if self._cap is None or not self._cap.isOpened():
            return False
        
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        log.info(f"Camera {self._index} resolution set to {width}x{height}")
        return True
