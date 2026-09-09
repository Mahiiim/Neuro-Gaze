"""
ui/dashboard.py
----------------
Dashboard page — live webcam feed, EAR display, and tracking controls.

All colour tokens are read from ``ui.theme`` so that Dark / Light / High-
Contrast themes apply automatically.
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
from ui.components import DwellButton
from ui.theme import T, S, theme_manager
from utils.config import Config
from utils.logger import get_logger

log = get_logger(__name__)


class _StatCard(QFrame):
    """Small info card used in the status grid."""

    def __init__(self, title: str, initial: str = "—", parent=None) -> None:
        super().__init__(parent)
        self._title = title
        self.setFixedHeight(S(74))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(S(14), S(8), S(14), S(8))
        layout.setSpacing(S(4))

        self._title_lbl = QLabel(title)
        self._value_lbl = QLabel(initial)
        layout.addWidget(self._title_lbl)
        layout.addWidget(self._value_lbl)

        self._value_color = T("TEXT_PRIMARY")
        self._apply_theme()
        theme_manager().theme_changed.connect(self._apply_theme)

    def set_value(self, text: str, color: str | None = None) -> None:
        if color is not None:
            self._value_color = color
        self._value_lbl.setText(text)
        self._value_lbl.setStyleSheet(
            f"color:{self._value_color}; font-size:{S(20)}px; font-weight:700; border:none;"
        )

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            f"background:{T('BG_CARD')}; border:1px solid {T('BORDER_SOLID')}; border-radius:{S(8)}px;"
        )
        self._title_lbl.setStyleSheet(
            f"color:{T('TEXT_MUTED')}; font-size:{S(11)}px; border:none;"
        )
        self._value_lbl.setStyleSheet(
            f"color:{self._value_color}; font-size:{S(20)}px; font-weight:700; border:none;"
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
        self._apply_theme()
        self._connect_tracker()
        theme_manager().theme_changed.connect(self._apply_theme)

    # ── public property for MainWindow frame routing ─────────────

    @property
    def cam_label(self) -> QLabel:
        """Expose the camera QLabel so MainWindow can render frames to it."""
        return self._cam_label

    # ── UI construction ─────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(S(20), S(20), S(20), S(20))
        outer.setSpacing(S(16))

        # LEFT: Camera feed + controls
        left = QVBoxLayout()
        left.setSpacing(S(12))

        # Camera feed label
        self._cam_label = QLabel()
        self._cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cam_label.setMinimumSize(640, 480)
        self._cam_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._cam_label.setText("⏳  Initialising camera…")
        self._cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left.addWidget(self._cam_label, 1)

        # Camera controls row
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(S(10))

        self._btn_start = DwellButton("▶  START TRACKING", dwell_ms=1000)
        self._btn_start.clicked.connect(self._start_tracking)
        ctrl_row.addWidget(self._btn_start)

        self._btn_stop = DwellButton("🛑  STOP TRACKING", dwell_ms=1000)
        self._btn_stop.clicked.connect(self._stop_tracking)
        self._btn_stop.setEnabled(False)
        ctrl_row.addWidget(self._btn_stop)
        ctrl_row.addStretch(1)
        left.addLayout(ctrl_row)

        outer.addLayout(left, 3)

        # RIGHT: Status cards
        right = QVBoxLayout()
        right.setSpacing(S(10))

        self._right_title = QLabel("Live Status")
        right.addWidget(self._right_title)

        # Stat cards
        self._card_ear = _StatCard("Eye Aspect Ratio", "—")
        self._card_eye = _StatCard("Eye Status", "OPEN")
        self._card_face = _StatCard("Face", "Not Detected")
        self._card_tracking = _StatCard("Tracking", "OFF")

        for card in (self._card_ear, self._card_eye, self._card_face, self._card_tracking):
            right.addWidget(card)

        right.addSpacing(S(16))

        # EAR threshold display
        self._thr_lbl = QLabel("Blink Threshold")
        self._thr_value = QLabel(f"{self._config.get('blink_threshold', 0.20):.2f}")
        right.addWidget(self._thr_lbl)
        right.addWidget(self._thr_value)

        right.addStretch(1)

        # Quick hint
        self._hint = QLabel(
            "💡 Head movement → Mouse\n"
            "👁️ Blink → Click\n"
            "Press ESC to emergency stop"
        )
        self._hint.setWordWrap(True)
        right.addWidget(self._hint)

        outer.addLayout(right, 1)

    # ── theme application ────────────────────────────────────────

    def _apply_theme(self) -> None:
        """Refresh all dashboard styles from the active theme palette."""
        self._cam_label.setStyleSheet(
            f"background:{T('BG_CARD')}; border:2px solid {T('BORDER_SOLID')}; border-radius:{S(10)}px;"
        )
        self._btn_start.setStyleSheet(
            f"background:{T('ACCENT')}; color:{T('KEY_HOVER_TEXT')}; border:none; border-radius:{S(8)}px;"
            f"padding:{S(10)}px {S(28)}px; font-size:{S(14)}px; font-weight:700;"
        )
        self._btn_stop.setStyleSheet(
            f"background:{T('BORDER_SOLID')}; color:{T('TEXT_PRIMARY')}; border:none; border-radius:{S(8)}px;"
            f"padding:{S(10)}px {S(28)}px; font-size:{S(14)}px; font-weight:600;"
        )
        self._right_title.setStyleSheet(
            f"color:{T('TEXT_PRIMARY')}; font-size:{S(16)}px; font-weight:700;"
        )
        self._thr_lbl.setStyleSheet(f"color:{T('TEXT_MUTED')}; font-size:{S(11)}px;")
        self._thr_value.setStyleSheet(
            f"color:{T('ACCENT')}; font-size:{S(15)}px; font-weight:700;"
        )
        self._hint.setStyleSheet(
            f"color:{T('TEXT_MUTED')}; font-size:{S(11)}px; "
            f"background:{T('BG_CARD')}; border:1px solid {T('BORDER_SOLID')}; border-radius:{S(8)}px; padding:{S(10)}px;"
        )

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
            color=T("DANGER") if blink else T("SUCCESS"),
        )
        self._thr_value.setText(f"{threshold:.2f}")

    def _on_face_detected(self, detected: bool) -> None:
        self._card_face.set_value(
            "✓ Detected" if detected else "✗ Not Detected",
            color=T("SUCCESS") if detected else T("DANGER"),
        )

    def _on_blink(self) -> None:
        self._card_eye.set_value("CLICK!", color=T("ACCENT"))

    def _start_tracking(self) -> None:
        self._tracker.start_tracking()
        self._tracking_on = True
        self._btn_start.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._card_tracking.set_value("ON", color=T("SUCCESS"))
        self.tracking_started.emit()
        log.info("Tracking started from dashboard")

    def _stop_tracking(self) -> None:
        self._tracker.stop_tracking()
        self._tracking_on = False
        self._btn_start.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._card_tracking.set_value("OFF", color=T("DANGER"))
        self.tracking_stopped.emit()
        log.info("Tracking stopped from dashboard")

    def on_external_stop(self) -> None:
        """Called from MainWindow emergency stop."""
        if self._tracking_on:
            self._tracking_on = False
            self._btn_start.setEnabled(True)
            self._btn_stop.setEnabled(False)
            self._card_tracking.set_value("STOPPED", color=T("DANGER"))
            self.tracking_stopped.emit()
