"""
ui/calibration.py
-----------------
Provides a 5-point calibration wizard to map the user's maximum head movement range.
Collects data from FaceTrackerWorker without triggering mouse movements.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from core.face_tracker import FaceTrackerWorker
from ui.components import DwellButton
from ui.theme import T, S, theme_manager
from utils.config import Config
from utils.logger import get_logger

log = get_logger(__name__)


class CalibrationWizardWidget(QWidget):
    """
    Guides the user through 5 points:
      1. Top-Left
      2. Top-Right
      3. Center
      4. Bottom-Left
      5. Bottom-Right
    """

    def __init__(self, config: Config, tracker: FaceTrackerWorker, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._tracker = tracker
        self._points: list[tuple[float, float]] = []
        self._current_step = -1
        self._collecting = False
        self._buffer: list[tuple[float, float]] = []
        self._all_ears: list[float] = []
        self._ear_buffer: list[float] = []

        self._build_ui()
        self._apply_theme()
        theme_manager().theme_changed.connect(self._apply_theme)

        # Listen for raw nose coordinates (always emitted by tracker, even if mouse is disabled)
        self._tracker.nose_position.connect(self._on_nose_position)
        self._tracker.ear_updated.connect(self._on_ear_updated)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(S(32), S(24), S(32), S(24))
        outer.setSpacing(S(16))

        # Header
        self._title = QLabel("🎯  Calibration Wizard")
        self._hint = QLabel(
            "Map your head movement bounds to comfortably reach all edges of the screen."
        )
        outer.addWidget(self._title)
        outer.addWidget(self._hint)

        # Main interactive area
        self._card = QFrame()
        self._card.setSizePolicy(
            self._card.sizePolicy().Policy.Expanding,
            self._card.sizePolicy().Policy.Expanding,
        )
        self._card_layout = QStackedLayout(self._card)
        outer.addWidget(self._card, 1)

        # -- Screen 0: Intro
        intro = QWidget()
        intro_ly = QVBoxLayout(intro)
        intro_ly.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._intro_lbl = QLabel(
            "We will calibrate your head movement.\n"
            "Look at the target dots when they appear, then stare at the button below to capture."
        )
        self._intro_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._btn_start = DwellButton("▶  Start Calibration", dwell_ms=1000)
        self._btn_start.clicked.connect(self._start_wizard)
        self._btn_start.setFixedSize(S(220), S(60))
        intro_ly.addWidget(self._intro_lbl)
        intro_ly.addSpacing(S(30))
        intro_ly.addWidget(self._btn_start, 0, Qt.AlignmentFlag.AlignHCenter)
        self._card_layout.addWidget(intro)

        # -- Screen 1: Active Calibration
        calib = QWidget()
        calib_ly = QVBoxLayout(calib)
        calib_ly.setContentsMargins(0, 0, 0, 0)
        
        self._target_lbl = QLabel("Target")
        self._target_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._target_lbl.setFixedSize(S(120), S(120))
        
        # We will manually move the target in the layout, so we use a container
        self._calib_container = QWidget()
        self._target_lbl.setParent(self._calib_container)
        calib_ly.addWidget(self._calib_container, 1)

        self._calib_status = QLabel("Look at the target")
        self._calib_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        calib_ly.addWidget(self._calib_status)

        self._btn_capture = DwellButton("👁️  Capture Point", dwell_ms=1200)
        self._btn_capture.clicked.connect(self._begin_capture)
        self._btn_capture.setMinimumHeight(S(70))
        calib_ly.addWidget(self._btn_capture)
        self._card_layout.addWidget(calib)

        # -- Screen 2: Finished
        done = QWidget()
        done_ly = QVBoxLayout(done)
        done_ly.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_lbl = QLabel("Calibration Complete!")
        self._done_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._btn_finish = DwellButton("✓  Save & Apply", dwell_ms=1000)
        self._btn_finish.clicked.connect(self._save_and_exit)
        self._btn_finish.setFixedSize(S(220), S(60))
        done_ly.addWidget(self._done_lbl)
        done_ly.addSpacing(S(30))
        done_ly.addWidget(self._btn_finish, 0, Qt.AlignmentFlag.AlignHCenter)
        self._card_layout.addWidget(done)

    def _apply_theme(self) -> None:
        self._title.setStyleSheet(
            f"color:{T('TEXT_PRIMARY')}; font-size:{S(20)}px; font-weight:700;"
        )
        self._hint.setStyleSheet(f"color:{T('TEXT_MUTED')}; font-size:{S(13)}px;")
        self._card.setStyleSheet(
            f"background:{T('BG_CARD')}; border:1px solid {T('BORDER_SOLID')}; border-radius:{S(14)}px;"
        )
        self._intro_lbl.setStyleSheet(f"color:{T('TEXT_PRIMARY')}; font-size:{S(16)}px;")
        self._calib_status.setStyleSheet(f"color:{T('ACCENT')}; font-size:{S(18)}px; font-weight:700;")
        self._target_lbl.setStyleSheet(
            f"background:{T('ACCENT')}; color:{T('KEY_HOVER_TEXT')}; "
            f"border-radius:{S(60)}px; font-size:{S(14)}px; font-weight:800;"
        )
        self._done_lbl.setStyleSheet(f"color:{T('SUCCESS')}; font-size:{S(22)}px; font-weight:700;")

    # ── Wizard flow ──────────────────────────────────────────────

    def _start_wizard(self) -> None:
        log.info("Starting calibration wizard")
        self._points.clear()
        self._all_ears.clear()
        self._current_step = 0
        self._card_layout.setCurrentIndex(1)
        self._tracker.stop_tracking()  # Ensure mouse doesn't move wildly during calibration
        self._place_target()

    def _place_target(self) -> None:
        """Move the target label to one of the 5 positions based on current step."""
        cw = self._calib_container.width()
        ch = self._calib_container.height()
        tw = self._target_lbl.width()
        th = self._target_lbl.height()
        margin = S(20)

        # 0: Top-Left, 1: Top-Right, 2: Center, 3: Bottom-Left, 4: Bottom-Right
        pos_map = {
            0: (margin, margin, "1 / 5\nTop-Left"),
            1: (cw - tw - margin, margin, "2 / 5\nTop-Right"),
            2: (cw // 2 - tw // 2, ch // 2 - th // 2, "3 / 5\nCenter"),
            3: (margin, ch - th - margin, "4 / 5\nBottom-Left"),
            4: (cw - tw - margin, ch - th - margin, "5 / 5\nBottom-Right"),
        }

        if self._current_step in pos_map:
            x, y, text = pos_map[self._current_step]
            self._target_lbl.setText(text)
            self._target_lbl.move(int(x), int(y))
            self._calib_status.setText("Look at the target, then stare at 'Capture'")
            self._btn_capture.setEnabled(True)

    def _begin_capture(self) -> None:
        """Start collecting nose positions for 1 second."""
        self._buffer.clear()
        self._ear_buffer.clear()
        self._collecting = True
        self._btn_capture.setEnabled(False)
        self._calib_status.setText("Capturing... Keep looking at target!")
        QTimer.singleShot(1000, self._finish_capture)

    def _on_nose_position(self, x: float, y: float) -> None:
        """Records nose coordinates if a capture is currently active."""
        if self._collecting:
            self._buffer.append((x, y))
            
    def _on_ear_updated(self, ear: float) -> None:
        if self._collecting and ear > 0.0:
            self._ear_buffer.append(ear)

    def _finish_capture(self) -> None:
        self._collecting = False
        if not self._buffer:
            log.warning("No data collected during capture window")
            self._calib_status.setText("Error: Face lost! Try again.")
            self._btn_capture.setEnabled(True)
            return

        # Calculate robust mean for this point
        xs = [p[0] for p in self._buffer]
        ys = [p[1] for p in self._buffer]
        mx, my = np.median(xs), np.median(ys)
        
        self._points.append((float(mx), float(my)))
        self._all_ears.extend(self._ear_buffer)
        log.debug("Captured point %d: (%.3f, %.3f) with %d EAR samples", self._current_step, mx, my, len(self._ear_buffer))

        self._current_step += 1
        if self._current_step < 5:
            self._place_target()
        else:
            self._card_layout.setCurrentIndex(2)

    def _save_and_exit(self) -> None:
        """Calculate final bounds from the 5 points and save to config."""
        xs = [p[0] for p in self._points]
        ys = [p[1] for p in self._points]

        # In MediaPipe mirrored view: 
        # looking right -> smaller x, looking left -> larger x
        # looking up -> smaller y, looking down -> larger y
        
        # Calculate raw bounds
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        # Apply 10% padding so the user can easily reach the very edges
        pad_x = (max_x - min_x) * 0.10
        pad_y = (max_y - min_y) * 0.10

        final_min_x = max(0.0, min_x + pad_x)
        final_max_x = min(1.0, max_x - pad_x)
        final_min_y = max(0.0, min_y + pad_y)
        final_max_y = min(1.0, max_y - pad_y)

        # Safeguard against totally collapsed bounds (e.g. tracking froze)
        if (final_max_x - final_min_x) < 0.05:
            final_min_x, final_max_x = 0.38, 0.62
        if (final_max_y - final_min_y) < 0.05:
            final_min_y, final_max_y = 0.38, 0.62

        log.info("Calibration finished. X:[%.3f - %.3f] Y:[%.3f - %.3f]", 
                 final_min_x, final_max_x, final_min_y, final_max_y)

        self._config.set("range_x_min", float(final_min_x))
        self._config.set("range_x_max", float(final_max_x))
        self._config.set("range_y_min", float(final_min_y))
        self._config.set("range_y_max", float(final_max_y))
        
        # Adaptive EAR Calculation
        if self._all_ears:
            # Drop the top and bottom 10% of outliers
            sorted_ears = sorted(self._all_ears)
            trim = max(1, len(sorted_ears) // 10)
            trimmed_ears = sorted_ears[trim:-trim] if len(sorted_ears) > 2 else sorted_ears
            
            baseline_ear = np.mean(trimmed_ears)
            # Set blink threshold to exactly 20% below the baseline open eye EAR
            new_threshold = round(baseline_ear * 0.80, 2)
            # Bound the threshold to sane defaults
            new_threshold = max(0.10, min(new_threshold, 0.45))
            
            log.info("Adaptive EAR: baseline=%.3f, new_threshold=%.3f", baseline_ear, new_threshold)
            self._config.set("blink_threshold", float(new_threshold))
        
        # Hot-reload into the tracker
        self._tracker.update_config(self._config)
        self._config.save()

        # Reset UI
        self._card_layout.setCurrentIndex(0)

    def resizeEvent(self, event) -> None:
        """Ensure the target dot stays positioned correctly if window is resized."""
        super().resizeEvent(event)
        if self._card_layout.currentIndex() == 1:
            self._place_target()
