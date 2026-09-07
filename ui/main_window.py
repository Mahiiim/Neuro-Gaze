"""
ui/main_window.py
------------------
Root QMainWindow for NeuroVision.

Layout
------
  ┌─────────────────────────────────────────────────────┐
  │  Header: title + subtitle + status pills            │
  ├──────────┬──────────────────────────────────────────┤
  │ Sidebar  │  QStackedWidget (page area)              │
  │  nav     │                                          │
  │  buttons │                                          │
  ├──────────┴──────────────────────────────────────────┤
  │  Emergency Stop bar (always visible)                │
  └─────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSize, QTimer, QVariantAnimation
from PySide6.QtGui import QFont, QIcon, QKeySequence, QShortcut, QColor, QPainter, QBrush, QPixmap, QImage
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QFrame,
    QMessageBox,
    QGraphicsDropShadowEffect,
)

from core.face_tracker import FaceTrackerWorker
from core.speech_engine import SpeechEngine
from ui.about import AboutWidget
from ui.dashboard import DashboardWidget
from ui.keyboard import KeyboardWidget
from ui.phrases import PhrasesWidget
from ui.settings import SettingsWidget
from ui.wheelchair import WheelchairWidget
from ui.home_automation import HomeAutomationWidget
from utils.config import Config
from utils.logger import get_logger

log = get_logger(__name__)

# ── Colour palette ────────────────────────────────────────────
BG_DARK = "#0A1118"
BG_PANEL = "#101F30"
BG_SIDEBAR = "#0A1118"
ACCENT = "#00D2FF"
ACCENT_HOVER = "#00F5D4"
TEXT_PRIMARY = "#FFFFFF"
TEXT_MUTED = "#A0B2C6"
BORDER = "rgba(255, 255, 255, 0.1)"
SUCCESS = "#2ED573"
WARNING = "#FFA502"
DANGER = "#FF4757"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Inter', sans-serif;
}}
QFrame#sidebar {{
    background-color: {BG_SIDEBAR};
    border-right: 1px solid {BORDER};
}}
QPushButton#navBtn {{
    background-color: rgba(255, 255, 255, 0.05);
    color: {TEXT_MUTED};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 14px 20px;
    font-size: 15px;
    text-align: left;
    font-weight: 500;
}}
QPushButton#navBtn[active="true"] {{
    color: {TEXT_PRIMARY};
    border: 1px solid {ACCENT};
    background-color: rgba(0, 210, 255, 0.15);
    font-weight: 700;
}}
QPushButton#emergencyBtn {{
    background-color: {DANGER};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 30px;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
}}
QPushButton#emergencyBtn:hover {{
    background-color: #ff6b6b;
}}
QFrame#header {{
    background-color: {BG_PANEL};
    border-bottom: 1px solid {BORDER};
}}
QLabel#appTitle {{
    font-size: 22px;
    font-weight: 800;
    color: {ACCENT};
    letter-spacing: 2px;
}}
QLabel#appSubtitle {{
    font-size: 11px;
    color: {TEXT_MUTED};
    letter-spacing: 0.5px;
}}
"""


class GazeNavButton(QPushButton):
    """A button that triggers a visual progress indicator and clicks automatically after dwelling."""
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setObjectName("navBtn")
        self.setMinimumHeight(72)
        
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(600)
        self._hover_timer.timeout.connect(self.click)
        
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(600)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(100.0)
        self._anim.valueChanged.connect(self._on_anim)
        
        self._progress = 0.0
        
    def _on_anim(self, val):
        self._progress = val
        self.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        self._hover_timer.start()
        self._anim.start()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._hover_timer.stop()
        self._anim.stop()
        self._progress = 0.0
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self._progress > 0 and self.property("active") != "true":
            painter = QPainter(self)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(ACCENT_HOVER))
            painter.setOpacity(0.2)
            w = int(self.width() * (self._progress / 100.0))
            painter.drawRoundedRect(0, 0, w, self.height(), 12, 12)
            painter.end()


class StatusPill(QLabel):
    """A small coloured pill label for header status indicators."""

    def __init__(self, label: str, parent=None) -> None:
        super().__init__(parent)
        self._label = label
        self._ok = False
        self._refresh()
        self.setFixedHeight(24)
        self.setContentsMargins(10, 2, 10, 2)

    def set_ok(self, ok: bool, text: str = "") -> None:
        self._ok = ok
        self._text = text
        self._refresh()

    def _refresh(self) -> None:
        text = getattr(self, "_text", "")
        color = SUCCESS if self._ok else DANGER
        display = text if text else ("●" if self._ok else "○")
        self.setText(f"  {self._label}: {display}  ")
        bg_rgb = "46,213,115" if self._ok else "255,71,87"
        self.setStyleSheet(
            f"background-color: rgba({bg_rgb}, 0.15);"
            f"color: {color};"
            f"border: 1px solid {color};"
            f"border-radius: 12px;"
            f"font-size: 11px; font-weight: 600;"
        )


class MainWindow(QMainWindow):
    """Root application window."""

    # Page indices in the QStackedWidget
    PAGE_DASHBOARD = 0
    PAGE_WHEELCHAIR = 1
    PAGE_HOME = 2
    PAGE_KEYBOARD = 3
    PAGE_PHRASES = 4
    PAGE_SETTINGS = 5
    PAGE_ABOUT = 6

    def __init__(self, config: Config, tracker: FaceTrackerWorker, speech: SpeechEngine) -> None:
        super().__init__()
        self._config = config
        self._tracker = tracker
        self._speech = speech

        self.setWindowTitle("NeuroVision — Eye-Controlled Assistive Ecosystem")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._connect_signals()
        self._wire_tracker()

        # ESC = emergency stop
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self._emergency_stop)

        log.info("MainWindow initialised")

    # ── UI construction ─────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        outer.addWidget(self._build_header())

        # Body (sidebar + pages)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        self._pages_container = self._build_pages()
        body.addWidget(self._pages_container, 1)
        outer.addLayout(body, 1)

        # Emergency stop bar
        outer.addWidget(self._build_emergency_bar())

        # PiP camera overlay — parented to the pages container so it
        # floats above page content but stays inside the workspace area.
        self._build_pip_overlay()

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("header")
        frame.setFixedHeight(68)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(24, 0, 24, 0)

        # Title block
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        title = QLabel("NEUROVISION")
        title.setObjectName("appTitle")
        subtitle = QLabel("Eye-Controlled Assistive Communication System")
        subtitle.setObjectName("appSubtitle")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        layout.addLayout(title_block)
        layout.addStretch(1)

        # Status pills
        self._pill_camera = StatusPill("Camera")
        self._pill_face = StatusPill("Face")
        self._pill_tracking = StatusPill("Tracking")
        self._pill_voice = StatusPill("Voice")

        for pill in (self._pill_camera, self._pill_face, self._pill_tracking, self._pill_voice):
            layout.addWidget(pill)
            layout.addSpacing(6)

        return frame

    def _build_sidebar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("sidebar")
        frame.setFixedWidth(280)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 24, 12, 24)
        layout.setSpacing(12)

        nav_items = [
            ("🏠  Dashboard", self.PAGE_DASHBOARD),
            ("🦽  Wheelchair Drive", self.PAGE_WHEELCHAIR),
            ("💡  Home Automation", self.PAGE_HOME),
            ("⌨️  Eye Keyboard", self.PAGE_KEYBOARD),
            ("💬  Quick Phrases", self.PAGE_PHRASES),
            ("⚙️  Settings", self.PAGE_SETTINGS),
            ("ℹ️  About", self.PAGE_ABOUT),
        ]
        self._nav_buttons: dict[int, GazeNavButton] = {}
        for label, page_idx in nav_items:
            btn = GazeNavButton(label)
            btn.setCheckable(False)
            btn.setProperty("active", "false")
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, p=page_idx: self._navigate(p))
            layout.addWidget(btn)
            self._nav_buttons[page_idx] = btn

        layout.addStretch(1)
        return frame

    def _build_pages(self) -> QStackedWidget:
        self._pages = QStackedWidget()

        self._dashboard = DashboardWidget(self._config, self._tracker, self._speech)
        self._wheelchair = WheelchairWidget()
        self._home_automation = HomeAutomationWidget(self._speech)
        self._keyboard = KeyboardWidget(self._speech)
        self._phrases = PhrasesWidget(self._config, self._speech)
        self._settings = SettingsWidget(self._config, self._tracker, self._speech)
        self._about = AboutWidget()

        self._pages.addWidget(self._dashboard)         # 0
        self._pages.addWidget(self._wheelchair)        # 1
        self._pages.addWidget(self._home_automation)   # 2
        self._pages.addWidget(self._keyboard)          # 3
        self._pages.addWidget(self._phrases)           # 4
        self._pages.addWidget(self._settings)          # 5
        self._pages.addWidget(self._about)             # 6

        self._navigate(self.PAGE_DASHBOARD)
        return self._pages

    # ── PiP camera overlay ───────────────────────────────────────

    def _build_pip_overlay(self) -> None:
        """Create the floating Picture-in-Picture camera preview."""
        PIP_W, PIP_H = 260, 180  # container size (feed + telemetry)
        FEED_W, FEED_H = 240, 135  # 16:9 camera feed

        # Main PiP container — parented to the pages widget so it overlays
        self._pip_container = QFrame(self._pages_container)
        self._pip_container.setObjectName("pipContainer")
        self._pip_container.setFixedSize(PIP_W, PIP_H)
        self._pip_container.setStyleSheet(
            f"QFrame#pipContainer {{"
            f"  background-color: {BG_PANEL};"
            f"  border: 2px solid {ACCENT_HOVER};"
            f"  border-radius: 14px;"
            f"}}"
        )

        # Drop-shadow effect
        shadow = QGraphicsDropShadowEffect(self._pip_container)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 153))  # rgba(0,0,0,0.6)
        self._pip_container.setGraphicsEffect(shadow)

        pip_layout = QVBoxLayout(self._pip_container)
        pip_layout.setContentsMargins(10, 10, 10, 6)
        pip_layout.setSpacing(4)

        # Camera feed label
        self._pip_cam_label = QLabel()
        self._pip_cam_label.setFixedSize(FEED_W, FEED_H)
        self._pip_cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pip_cam_label.setStyleSheet(
            "background: #0A1118; border-radius: 8px; border: none;"
        )
        pip_layout.addWidget(self._pip_cam_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Telemetry pill bar (EAR + face dot)
        telemetry_row = QHBoxLayout()
        telemetry_row.setContentsMargins(4, 0, 4, 0)
        telemetry_row.setSpacing(6)

        self._pip_face_dot = QLabel("●")
        self._pip_face_dot.setFixedSize(18, 18)
        self._pip_face_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pip_face_dot.setStyleSheet(
            f"color: {ACCENT_HOVER}; font-size: 12px; border: none;"
        )
        telemetry_row.addWidget(self._pip_face_dot)

        self._pip_status_label = QLabel("FACE OK")
        self._pip_status_label.setStyleSheet(
            f"color: {ACCENT_HOVER}; font-size: 10px; font-weight: 600; border: none;"
        )
        telemetry_row.addWidget(self._pip_status_label)

        telemetry_row.addStretch(1)

        self._pip_ear_label = QLabel("EAR: —")
        self._pip_ear_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 10px; font-weight: 600;"
            f" background: rgba(10,17,24,0.7); border-radius: 6px;"
            f" padding: 2px 6px; border: none;"
        )
        telemetry_row.addWidget(self._pip_ear_label)

        pip_layout.addLayout(telemetry_row)

        # Face-lost flash timer
        self._pip_face_ok = True
        self._pip_border_visible = True
        self._pip_flash_timer = QTimer(self)
        self._pip_flash_timer.setInterval(500)
        self._pip_flash_timer.timeout.connect(self._pip_flash_border)

        # Start hidden (Dashboard is the default page)
        self._pip_container.hide()
        self._reposition_pip()

    def _build_emergency_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(f"background-color: {BG_PANEL}; border-top: 1px solid {BORDER};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 10, 24, 10)

        hint = QLabel("ESC — Stop Mouse  |  DANGER — Alert Others")
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 13px;")
        layout.addWidget(hint, 1)

        self._btn_alert = QPushButton("🚨  PATIENT EMERGENCY ALERT")
        self._btn_alert.setObjectName("alertBtn")
        self._btn_alert.setFixedHeight(52)
        self._btn_alert.setStyleSheet(f"""
            QPushButton#alertBtn {{
                background-color: #FF0000;
                color: white;
                border: 2px solid #AA0000;
                border-radius: 8px;
                padding: 10px 30px;
                font-size: 16px;
                font-weight: 900;
                letter-spacing: 1px;
            }}
            QPushButton#alertBtn:hover {{
                background-color: #FF3333;
                border: 2px solid #FF0000;
            }}
        """)
        self._btn_alert.clicked.connect(self._trigger_patient_alert)
        layout.addWidget(self._btn_alert)
        
        layout.addSpacing(15)

        self._btn_emergency = QPushButton("🛑  EMERGENCY STOP")
        self._btn_emergency.setObjectName("emergencyBtn")
        self._btn_emergency.setFixedHeight(52)
        self._btn_emergency.setStyleSheet(f"""
            QPushButton#emergencyBtn {{
                background-color: {DANGER};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 30px;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QPushButton#emergencyBtn:hover {{
                background-color: #ff6b6b;
            }}
        """)
        self._btn_emergency.clicked.connect(self._emergency_stop)
        layout.addWidget(self._btn_emergency)

        return bar

    # ── signal wiring ────────────────────────────────────────────

    def _connect_signals(self) -> None:
        # Speech status → Voice pill
        self._speech.speaking_started.connect(
            lambda: self._pill_voice.set_ok(True, "Speaking…")
        )
        self._speech.speaking_finished.connect(
            lambda: self._pill_voice.set_ok(True, "Ready")
        )

    def _wire_tracker(self) -> None:
        """Connect tracker signals to header status pills, pages, and PiP."""
        self._tracker.face_detected.connect(
            lambda ok: self._pill_face.set_ok(ok, "Detected" if ok else "Not Detected")
        )
        self._tracker.tracking_error.connect(self._on_tracking_error)

        # Camera pill — set to connected once thread starts
        self._pill_camera.set_ok(True, "Connected")
        self._pill_tracking.set_ok(False, "OFF")

        # Dashboard signals
        self._dashboard.tracking_started.connect(
            lambda: self._pill_tracking.set_ok(True, "ON")
        )
        self._dashboard.tracking_stopped.connect(
            lambda: self._pill_tracking.set_ok(False, "OFF")
        )

        # ── Centralised frame routing ────────────────────────────
        self._tracker.frame_ready.connect(self._dispatch_frame)

        # ── PiP telemetry signals ────────────────────────────────
        self._tracker.face_detected.connect(self._pip_on_face_detected)
        self._tracker.ear_updated.connect(self._pip_on_ear_updated)

    # ── navigation ───────────────────────────────────────────────

    def _navigate(self, page_idx: int) -> None:
        self._pages.setCurrentIndex(page_idx)
        for idx, btn in self._nav_buttons.items():
            btn.setProperty("active", "true" if idx == page_idx else "false")
            # Force style refresh
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        # Toggle PiP visibility (guard needed: first _navigate call
        # happens inside _build_pages before _build_pip_overlay runs)
        if hasattr(self, '_pip_container'):
            if page_idx == self.PAGE_DASHBOARD:
                self._pip_container.hide()
            else:
                self._pip_container.show()
                self._pip_container.raise_()  # ensure it's on top
                self._reposition_pip()

        log.debug("Navigated to page %d", page_idx)

    # ── emergency stop ────────────────────────────────────────────

    def _emergency_stop(self) -> None:
        self._tracker.emergency_stop()
        self._dashboard.on_external_stop()
        self._pill_tracking.set_ok(False, "STOPPED")
        log.warning("Emergency stop triggered from MainWindow")

    # ── PiP frame routing and telemetry ───────────────────────────

    def _dispatch_frame(self, image: QImage) -> None:
        """Route each frame to the correct display target."""
        if self._pages.currentIndex() == self.PAGE_DASHBOARD:
            # Full-size rendering on Dashboard
            pix = QPixmap.fromImage(image)
            cam = self._dashboard.cam_label
            scaled = pix.scaled(
                cam.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            cam.setPixmap(scaled)
        else:
            # Compact PiP rendering
            pix = QPixmap.fromImage(image)
            scaled = pix.scaled(
                self._pip_cam_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._pip_cam_label.setPixmap(scaled)

    def _pip_on_face_detected(self, detected: bool) -> None:
        """Update the PiP border glow and face-status dot."""
        self._pip_face_ok = detected
        if detected:
            self._pip_flash_timer.stop()
            self._pip_container.setStyleSheet(
                f"QFrame#pipContainer {{"
                f"  background-color: {BG_PANEL};"
                f"  border: 2px solid {ACCENT_HOVER};"
                f"  border-radius: 14px;"
                f"}}"
            )
            self._pip_face_dot.setStyleSheet(
                f"color: {ACCENT_HOVER}; font-size: 12px; border: none;"
            )
            self._pip_status_label.setText("FACE OK")
            self._pip_status_label.setStyleSheet(
                f"color: {ACCENT_HOVER}; font-size: 10px; font-weight: 600; border: none;"
            )
        else:
            self._pip_face_dot.setStyleSheet(
                f"color: {DANGER}; font-size: 12px; border: none;"
            )
            self._pip_status_label.setText("FACE LOST")
            self._pip_status_label.setStyleSheet(
                f"color: {DANGER}; font-size: 10px; font-weight: 600; border: none;"
            )
            if not self._pip_flash_timer.isActive():
                self._pip_border_visible = True
                self._pip_flash_timer.start()

    def _pip_flash_border(self) -> None:
        """Toggle the PiP border between red and transparent for a flashing alert."""
        self._pip_border_visible = not self._pip_border_visible
        border_color = DANGER if self._pip_border_visible else "transparent"
        self._pip_container.setStyleSheet(
            f"QFrame#pipContainer {{"
            f"  background-color: {BG_PANEL};"
            f"  border: 2px solid {border_color};"
            f"  border-radius: 14px;"
            f"}}"
        )

    def _pip_on_ear_updated(self, ear: float) -> None:
        """Update the EAR readout on the PiP telemetry pill."""
        if ear > 0:
            self._pip_ear_label.setText(f"EAR: {ear:.2f}")
        else:
            self._pip_ear_label.setText("EAR: —")

    def _reposition_pip(self) -> None:
        """Anchor the PiP container to the bottom-right of the pages area."""
        parent = self._pages_container
        margin = 16
        x = parent.width() - self._pip_container.width() - margin
        y = parent.height() - self._pip_container.height() - margin
        self._pip_container.move(max(0, x), max(0, y))

    def resizeEvent(self, event) -> None:
        """Reposition PiP when the window is resized."""
        super().resizeEvent(event)
        if hasattr(self, '_pip_container'):
            self._reposition_pip()

    def _trigger_patient_alert(self) -> None:
        log.warning("PATIENT EMERGENCY ALERT TRIGGERED!")
        self._emergency_stop()  # Also stop the mouse
        
        # Play a huge warning sound in a background thread
        import threading
        import winsound

        def _play_alarm():
            for _ in range(15):
                winsound.Beep(1500, 400)
                winsound.Beep(1000, 400)
                
        t = threading.Thread(target=_play_alarm, daemon=True)
        t.start()
        
        self._speech.speak("Emergency! Emergency! The patient requires immediate assistance!")
        QMessageBox.critical(self, "EMERGENCY ALERT", "PATIENT HAS TRIGGERED THE EMERGENCY ALERT!\nAssistance is required immediately.")

    def _on_tracking_error(self, message: str) -> None:
        self._pill_camera.set_ok(False, "Error")
        QMessageBox.critical(self, "Tracking Error", message)

    # ── cleanup ──────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        log.info("Application closing")
        self._tracker.stop_tracking()
        self._tracker.stop_thread()
        self._tracker.wait(3000)
        self._config.save()
        event.accept()
