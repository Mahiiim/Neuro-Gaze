"""
core/face_tracker.py
---------------------
QThread-based face tracking worker.

The worker runs an infinite loop that:
  1. Reads a frame from CameraManager
  2. Runs MediaPipe Face Landmarker inference
  3. Calls EAR calculation
  4. Calls MouseController for nose-based cursor movement
  5. Issues a click if a blink is detected
  6. Draws optional overlays onto the frame
  7. Converts the frame to QImage and emits it as a signal

All processing happens on a background thread; the GUI thread only
receives signals and updates widgets.
"""

from __future__ import annotations

import time
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from core.camera import CameraManager, get_model_path
from core.eye_tracker import calculate_ear, eye_status_label, is_blink
from core.mouse_controller import MouseController
from utils.config import Config
from utils.logger import get_logger

log = get_logger(__name__)


def _frame_to_qimage(frame: np.ndarray) -> QImage:
    """Convert a BGR OpenCV frame to a QImage (RGB888)."""
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    return QImage(rgb.data.tobytes(), w, h, ch * w, QImage.Format.Format_RGB888)


class FaceTrackerWorker(QThread):
    """
    Background thread that runs the full eye-tracking pipeline.

    Signals
    -------
    frame_ready(QImage)      — processed frame (with overlays) for display
    ear_updated(float)       — current EAR value
    face_detected(bool)      — whether a face was found in this frame
    blink_detected()         — fired once per confirmed blink-click
    nose_position(float, float) — normalised nose (x, y) in [0, 1]
    tracking_error(str)      — human-readable error message
    """

    frame_ready = Signal(QImage)
    ear_updated = Signal(float)
    face_detected = Signal(bool)
    blink_detected = Signal()
    nose_position = Signal(float, float)
    tracking_error = Signal(str)

    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._running = False
        self._tracking_active = False  # mouse control on/off
        self._fatigue_mode = False
        self._show_landmarks = True
        self._camera = CameraManager()
        self._mouse = MouseController()
        self._detector: Optional[mp_vision.FaceLandmarker] = None
        self._apply_config()

    # ── public API (called from GUI thread) ─────────────────────

    def start_tracking(self) -> None:
        """Enable mouse control."""
        self._mouse.enable()
        self._mouse.reset_position()
        self._tracking_active = True
        log.info("Tracking enabled")

    def stop_tracking(self) -> None:
        """Disable mouse control (camera feed continues)."""
        self._mouse.disable()
        self._tracking_active = False
        log.info("Tracking disabled")

    def emergency_stop(self) -> None:
        """Immediately disable all mouse interaction."""
        self.stop_tracking()
        log.warning("Emergency stop activated")

    @property
    def is_tracking(self) -> bool:
        return self._tracking_active

    def update_config(self, config: Config) -> None:
        """Hot-reload configuration changes."""
        self._config = config
        self._apply_config()

    def set_show_landmarks(self, show: bool) -> None:
        self._show_landmarks = show

    def stop_thread(self) -> None:
        """Signal the run loop to exit."""
        self._running = False
        self._tracking_active = False

    # ── QThread entry point ─────────────────────────────────────

    def run(self) -> None:
        """Main thread loop. Called by QThread.start()."""
        log.info("FaceTrackerWorker starting")
        self._running = True

        # Initialise MediaPipe detector
        try:
            self._detector = self._create_detector()
        except Exception as exc:
            msg = f"Failed to initialise face detector: {exc}"
            log.error(msg)
            self.tracking_error.emit(msg)
            return

        # Open camera
        cam_index = self._config.get("camera_index", 0)
        cam_w = self._config.get("camera_width", 640)
        cam_h = self._config.get("camera_height", 480)
        if not self._camera.open(cam_index, cam_w, cam_h):
            msg = (
                f"Camera {cam_index} could not be opened. "
                "Please connect a webcam and restart."
            )
            log.error(msg)
            self.tracking_error.emit(msg)
            return

        log.info("FaceTrackerWorker loop started")

        frame_times = []
        current_res = "high"
        high_res_w, high_res_h = cam_w, cam_h
        low_res_w, low_res_h = 320, 240

        while self._running:
            success, frame = self._camera.read_frame()
            
            # FPS Tracking
            now = time.time()
            frame_times.append(now)
            if len(frame_times) > 30:
                frame_times.pop(0)
                
            fps = len(frame_times) / (frame_times[-1] - frame_times[0]) if len(frame_times) > 1 and frame_times[-1] != frame_times[0] else 30.0

            # Dynamic resolution downscaling if struggling
            if fps < 15 and current_res == "high" and len(frame_times) == 30:
                log.warning("FPS dropped to %.1f, lowering camera resolution to save CPU", fps)
                self._camera.set_resolution(low_res_w, low_res_h)
                current_res = "low"
                frame_times.clear() # Reset to avoid instant flapping
            elif fps > 28 and current_res == "low" and len(frame_times) == 30:
                log.info("FPS recovered to %.1f, restoring camera resolution", fps)
                self._camera.set_resolution(high_res_w, high_res_h)
                current_res = "high"
                frame_times.clear()

            if not success or frame is None:
                time.sleep(0.033)
                continue

            # Mirror the frame (selfie-view)
            frame = cv2.flip(frame, 1)

            # Run MediaPipe inference
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            try:
                result = self._detector.detect(mp_image)
            except Exception as exc:
                log.warning("Detection error: %s", exc)
                self.frame_ready.emit(_frame_to_qimage(frame))
                continue

            face_present = bool(result.face_landmarks)
            self.face_detected.emit(face_present)

            ear = 0.0
            if face_present:
                landmarks = result.face_landmarks[0]

                # EAR
                ear = calculate_ear(landmarks)
                self.ear_updated.emit(ear)

                # Nose position
                nose = landmarks[1]
                self.nose_position.emit(nose.x, nose.y)

                # Mouse movement
                if self._tracking_active:
                    self._mouse.process_nose(nose.x, nose.y)

                # Blink → click
                threshold = self._config.get("blink_threshold", 0.20)
                if self._fatigue_mode:
                    threshold *= 0.90  # 10% lower threshold if tired

                if self._tracking_active and is_blink(ear, threshold):
                    clicked = self._mouse.try_click()
                    if clicked:
                        self.blink_detected.emit()

                # Draw overlays
                if self._show_landmarks:
                    self._draw_landmarks(frame, landmarks, ear, threshold)
            else:
                self.ear_updated.emit(0.0)

            self.frame_ready.emit(_frame_to_qimage(frame))

        # Cleanup
        self._camera.release()
        if self._detector:
            self._detector.close()
        log.info("FaceTrackerWorker stopped")

    # ── private helpers ─────────────────────────────────────────

    def _apply_config(self) -> None:
        """Push current config values into the MouseController."""
        self._mouse.update_config(
            alpha_min=self._config.get("smoothing_alpha_min", 0.05),
            alpha_max=self._config.get("smoothing_alpha_max", 0.25),
            click_cooldown=self._config.get("click_cooldown", 1.0),
            range_x=(
                self._config.get("range_x_min", 0.38),
                self._config.get("range_x_max", 0.62),
            ),
            range_y=(
                self._config.get("range_y_min", 0.38),
                self._config.get("range_y_max", 0.62),
            ),
            sensitivity_x=self._config.get("sensitivity_x", 1.0),
            sensitivity_y=self._config.get("sensitivity_y", 1.0),
            fatigue_mode=self._config.get("fatigue_mode", False),
        )
        self._fatigue_mode = self._config.get("fatigue_mode", False)
        self._show_landmarks = self._config.get("show_landmarks", True)

    def _create_detector(self) -> mp_vision.FaceLandmarker:
        model_path = get_model_path()
        base_options = mp_python.BaseOptions(model_asset_path=model_path)
        options = mp_vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=False,
            num_faces=1,
        )
        return mp_vision.FaceLandmarker.create_from_options(options)

    def _draw_landmarks(
        self,
        frame: np.ndarray,
        landmarks: list,
        ear: float,
        threshold: float,
    ) -> None:
        """Draw key landmarks and status text onto the frame (in-place)."""
        h, w = frame.shape[:2]

        # Eye corners and lids for visualisation (Removed for cleaner UI)
        # Nose tracking point (Removed for cleaner UI)

        # EAR status overlay
        status = eye_status_label(ear, threshold)
        blink = is_blink(ear, threshold)
        color = (0, 80, 255) if blink else (0, 220, 120)

        cv2.putText(
            frame,
            f"EAR: {ear:.2f}  |  {status}",
            (10, h - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
        )

        # Tracking indicator
        track_label = "TRACKING ON" if self._tracking_active else "TRACKING OFF"
        track_color = (0, 220, 120) if self._tracking_active else (80, 80, 80)
        cv2.putText(
            frame, track_label, (10, 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.55, track_color, 2
        )
