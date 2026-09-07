"""
ui/dashboard.py
----------------
Dashboard page — live webcam feed, EAR display, and tracking controls.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QImage, QPixmap, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QGridLayout,
)

from core.face_tracker import FaceTrackerWorker
from core.speech_engine import SpeechEngine
from utils.config import Config
from utils.logger import get_logger

log = get_logger(__name__)

# ── colours (same palette as main_window) ─────────────────────
BG_PANEL = "#161b22"
BG_CARD = "#1c2128"
ACCENT = "#00b4ff"
TEXT_PRIMARY = "#e6edf3"
TEXT_MUTED = "#8b949e"
BORDER = "#30363d"
SUCCESS = "#3fb950"
DANGER = "#f85149"


class _StatCard(QFrame):
    """Small info card used in the status grid."""

    def __init__(self, title: str, initial: str = "—", parent=None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"background:{BG_CARD}; border:1px solid {BORDER}; border-radius:8px;"
        )
        self.setFixedHeight(74)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(4)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px; border:none;")
        self._value_lbl = QLabel(initial)
        self._value_lbl.setStyleSheet(
            f"color:{TEXT_PRIMARY}; font-size:20px; font-weight:700; border:none;"
        )
        layout.addWidget(self._title_lbl)
        layout.addWidget(self._value_lbl)

    def set_value(self, text: str, color: str = TEXT_PRIMARY) -> None:
        self._value_lbl.setText(text)
        self._value_lbl.setStyleSheet(
            f"color:{color}; font-size:20px; font-weight:700; border:none;"
        )


class DashboardWidget(QWidget):
    """Dashboard page with camera feed and tracking controls."""

    tracking_started = Signal()
    tracking_stopped = Signal()

    def __init__(self, config: Config, tracker: FaceTrackerWorker, speech: SpeechEngine) -> None:
        super().__init__()
        self._config = config
        self._tracker = tracker
        self._speech = speech
        self._tracking_on = False
        self._build_ui()
        self._connect_tracker()

    # ── public property for MainWindow frame routing ─────────────

    @property
    def cam_label(self) -> QLabel:
        """Expose the camera QLabel so MainWindow can render frames to it."""
        return self._cam_label

    # ── UI construction ─────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(16)

        # LEFT: Camera feed + controls
        left = QVBoxLayout()
        left.setSpacing(12)

        # Camera feed label
        self._cam_label = QLabel()
        self._cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cam_label.setMinimumSize(640, 480)
        self._cam_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._cam_label.setStyleSheet(
            f"background:{BG_CARD}; border:2px solid {BORDER}; border-radius:10px;"
        )
        self._cam_label.setText("⏳  Initialising camera…")
        self._cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self._cam_label, 1)

        # Camera controls row
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(10)

        self._btn_start = QPushButton("▶  START TRACKING")
        self._btn_start.setStyleSheet(
            f"background:{ACCENT}; color:#0d1117; border:none; border-radius:8px;"
            f"padding:10px 28px; font-size:14px; font-weight:700;"
        )
        self._btn_start.clicked.connect(self._start_tracking)

        self._btn_stop = QPushButton("■  STOP TRACKING")
        self._btn_stop.setStyleSheet(
            f"background:#30363d; color:{TEXT_PRIMARY}; border:none; border-radius:8px;"
            f"padding:10px 28px; font-size:14px; font-weight:600;"
        )
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._stop_tracking)

        ctrl_row.addWidget(self._btn_start)
        ctrl_row.addWidget(self._btn_stop)
        ctrl_row.addStretch(1)
        left.addLayout(ctrl_row)

        outer.addLayout(left, 3)

        # RIGHT: Status cards
        right = QVBoxLayout()
        right.setSpacing(10)

        right_title = QLabel("Live Status")
        right_title.setStyleSheet(
            f"color:{TEXT_PRIMARY}; font-size:16px; font-weight:700;"
        )
        right.addWidget(right_title)

        # Stat cards
        self._card_ear = _StatCard("Eye Aspect Ratio", "—")
        self._card_eye = _StatCard("Eye Status", "OPEN")
        self._card_face = _StatCard("Face", "Not Detected")
        self._card_tracking = _StatCard("Tracking", "OFF")

        for card in (self._card_ear, self._card_eye, self._card_face, self._card_tracking):
            right.addWidget(card)

        right.addSpacing(16)

        # EAR threshold display
        thr_lbl = QLabel("Blink Threshold")
        thr_lbl.setStyleSheet(f"color:{TEXT_MUTED}; font-size:11px;")
        self._thr_value = QLabel(f"{self._config.get('blink_threshold', 0.20):.2f}")
        self._thr_value.setStyleSheet(f"color:{ACCENT}; font-size:15px; font-weight:700;")
        right.addWidget(thr_lbl)
        right.addWidget(self._thr_value)

        right.addStretch(1)

        # Quick hint
        hint = QLabel(
            "💡 Head movement → Mouse\n"
            "👁️ Blink → Click\n"
            "Press ESC to emergency stop"
        )
        hint.setStyleSheet(
            f"color:{TEXT_MUTED}; font-size:11px; "
            f"background:{BG_CARD}; border:1px solid {BORDER}; border-radius:8px; padding:10px;"
        )
        hint.setWordWrap(True)
        right.addWidget(hint)

        outer.addLayout(right, 1)

    # ── tracker signal connections ───────────────────────────────

    def _connect_tracker(self) -> None:
        # NOTE: frame_ready is NOT connected here — MainWindow centralises
        # frame routing to either this widget's cam_label or the PiP overlay.
        self._tracker.ear_updated.connect(self._on_ear)
        self._tracker.face_detected.connect(self._on_face_detected)
        self._tracker.blink_detected.connect(self._on_blink)

    # ── slots ────────────────────────────────────────────────────

    def _on_frame(self, image: QImage) -> None:
        pix = QPixmap.fromImage(image)
        scaled = pix.scaled(
            self._cam_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._cam_label.setPixmap(scaled)

    def _on_ear(self, ear: float) -> None:
        threshold = self._config.get("blink_threshold", 0.20)
        self._card_ear.set_value(f"{ear:.3f}")
        blink = ear < threshold and ear > 0
        self._card_eye.set_value(
            "CLOSED ✦" if blink else "OPEN",
            color=DANGER if blink else SUCCESS,
        )
        self._thr_value.setText(f"{threshold:.2f}")

    def _on_face_detected(self, detected: bool) -> None:
        self._card_face.set_value(
            "✓ Detected" if detected else "✗ Not Detected",
            color=SUCCESS if detected else DANGER,
        )

    def _on_blink(self) -> None:
        self._card_eye.set_value("CLICK!", color=ACCENT)

    def _start_tracking(self) -> None:
        self._tracker.start_tracking()
        self._tracking_on = True
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._card_tracking.set_value("ON", color=SUCCESS)
        self.tracking_started.emit()
        log.info("Tracking started from dashboard")

    def _stop_tracking(self) -> None:
        self._tracker.stop_tracking()
        self._tracking_on = False
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._card_tracking.set_value("OFF", color=DANGER)
        self.tracking_stopped.emit()
        log.info("Tracking stopped from dashboard")

    def on_external_stop(self) -> None:
        """Called from MainWindow emergency stop."""
        if self._tracking_on:
            self._tracking_on = False
            self._btn_start.setEnabled(True)
            self._btn_stop.setEnabled(False)
            self._card_tracking.set_value("STOPPED", color=DANGER)
            self.tracking_stopped.emit()
