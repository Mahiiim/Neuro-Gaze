"""
ui/main_window.py
------------------
Root QMainWindow for Neuro-Gaze.

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
from core.webhook import CaregiverNotifier
from core.session import session_logger
from core.audio_synth import AudioSynth
from ui.about import AboutWidget
from ui.dashboard import DashboardWidget
from ui.keyboard import KeyboardWidget
from ui.phrases import PhrasesWidget
from ui.settings import SettingsWidget
from ui.wheelchair import WheelchairWidget
from ui.home_automation import HomeAutomationWidget
from ui.calibration import CalibrationWizardWidget
from ui.tutorial import TutorialOverlay
from ui.entertainment import EntertainmentWidget
from ui.theme import T, S, theme_manager, hex_to_rgba
from utils.config import Config
from utils.logger import get_logger

log = get_logger(__name__)


# ── Stylesheet generator ─────────────────────────────────────────

def _build_stylesheet() -> str:
    """Generate the global QMainWindow stylesheet from the active theme."""
    return f"""
QMainWindow, QWidget {{
    background-color: {T("BG_DARK")};
    color: {T("TEXT_PRIMARY")};
    font-family: 'Segoe UI', 'Inter', sans-serif;
}}
QFrame#sidebar {{
    background-color: {T("BG_SIDEBAR")};
    border-right: 1px solid {T("BORDER")};
}}
QPushButton#navBtn {{
    background-color: {T("NAV_BTN_BG")};
    color: {T("TEXT_MUTED")};
    border: 1px solid {T("BORDER")};
    border-radius: {S(12)}px;
    padding: {S(14)}px {S(20)}px;
    font-size: {S(15)}px;
    text-align: left;
    font-weight: 500;
}}
QPushButton#navBtn[active="true"] {{
    color: {T("TEXT_PRIMARY")};
    border: 1px solid {T("ACCENT")};
    background-color: {T("NAV_ACTIVE_BG")};
    font-weight: 700;
}}
QFrame#header {{
    background-color: {T("BG_PANEL")};
    border-bottom: 1px solid {T("BORDER")};
}}
QLabel#appTitle {{
    font-size: {S(22)}px;
    font-weight: 800;
    color: {T("ACCENT")};
    letter-spacing: 2px;
}}
QLabel#appSubtitle {{
    font-size: {S(11)}px;
    color: {T("TEXT_MUTED")};
    letter-spacing: 0.5px;
}}
"""


from ui.components import DwellButton


class StatusPill(QLabel):
    """A small coloured pill label for header status indicators."""

    def __init__(self, label: str, parent=None) -> None:
        super().__init__(parent)
        self._label = label
        self._ok = False
        self._refresh()
        self.setFixedHeight(S(24))
        self.setContentsMargins(S(10), S(2), S(10), S(2))
        theme_manager().theme_changed.connect(self._refresh)

    def set_ok(self, ok: bool, text: str = "") -> None:
        self._ok = ok
        self._text = text
        self._refresh()

    def _refresh(self) -> None:
        text = getattr(self, "_text", "")
        color = T("SUCCESS") if self._ok else T("DANGER")
        display = text if text else ("●" if self._ok else "○")
        self.setText(f"  {self._label}: {display}  ")
        bg = hex_to_rgba(color, 0.15)
        self.setStyleSheet(
            f"background-color: {bg};"
            f"color: {color};"
            f"border: 1px solid {color};"
            f"border-radius: {S(12)}px;"
            f"font-size: {S(11)}px; font-weight: 600;"
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
    PAGE_CALIBRATION = 7
    PAGE_ENTERTAINMENT = 8

    def __init__(self, config: Config, tracker: FaceTrackerWorker, speech: SpeechEngine) -> None:
        super().__init__()
        self._config = config
        self._tracker = tracker
        self._speech = speech
        self._audio = AudioSynth()

        self.setWindowTitle("Neuro-Gaze — Eye-Controlled Assistive Ecosystem")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)

        self._build_ui()
        self._apply_theme()          # initial style pass
        self._connect_signals()
        self._wire_tracker()

        # Tutorial overlay
        self._tutorial = TutorialOverlay(self)

        # ESC = emergency stop
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self._emergency_stop)
        
        # Emergency Flasher
        self._emergency_flash_timer = QTimer(self)
        self._emergency_flash_timer.setInterval(500)
        self._emergency_flash_timer.timeout.connect(self._flash_emergency_border)
        self._emergency_border_visible = False

        # Live theme switching — re-apply stylesheet + refresh PiP/emergency bar
        theme_manager().theme_changed.connect(self._apply_theme)

        session_logger.log_event("STARTUP", "Application started")
        log.info("MainWindow initialised")

    # ── theme application ────────────────────────────────────────

    def _apply_theme(self) -> None:
        """Rebuild all stylesheets from the active theme palette."""
        self.setStyleSheet(_build_stylesheet())

        # Emergency bar
        if hasattr(self, "_emergency_bar"):
            self._emergency_bar.setStyleSheet(
                f"background-color: {T('BG_PANEL')}; border-top: 1px solid {T('BORDER')};"
            )
        if hasattr(self, "_emergency_hint"):
            self._emergency_hint.setStyleSheet(
                f"color: {T('TEXT_MUTED')}; font-size: {S(13)}px;"
            )
        if hasattr(self, "_btn_alert"):
            self._btn_alert.setStyleSheet(f"""
                QPushButton#alertBtn {{
                    background-color: {T("ALERT_BG")};
                    color: white;
                    border: 2px solid {T("ALERT_BORDER")};
                    border-radius: {S(8)}px;
                    padding: {S(10)}px {S(30)}px;
                    font-size: {S(16)}px;
                    font-weight: 900;
                    letter-spacing: 1px;
                }}
                QPushButton#alertBtn:hover {{
                    background-color: {T("ALERT_HOVER")};
                    border: 2px solid {T("ALERT_BG")};
                }}
            """)
        if hasattr(self, "_btn_emergency"):
            self._btn_emergency.setStyleSheet(f"""
                QPushButton#emergencyBtn {{
                    background-color: {T("DANGER")};
                    color: white;
                    border: none;
                    border-radius: {S(8)}px;
                    padding: {S(10)}px {S(30)}px;
                    font-size: {S(15)}px;
                    font-weight: 700;
                    letter-spacing: 1px;
                }}
                QPushButton#emergencyBtn:hover {{
                    background-color: {T("EMERGENCY_HOVER")};
                }}
            """)

        # PiP overlay
        if hasattr(self, "_pip_container"):
            self._apply_pip_theme()

        # Force re-polish on nav buttons so the global stylesheet picks up
        if hasattr(self, "_nav_buttons"):
            for btn in self._nav_buttons.values():
                btn.style().unpolish(btn)
                btn.style().polish(btn)
                btn.update()

    def _apply_pip_theme(self) -> None:
        """Refresh PiP overlay colours from active theme."""
        self._pip_cam_label.setStyleSheet(
            f"background: {T('BG_DARK')}; border-radius: {S(8)}px; border: none;"
        )
        self._pip_ear_label.setStyleSheet(
            f"color: {T('TEXT_MUTED')}; font-size: {S(10)}px; font-weight: 600;"
            f" background: {hex_to_rgba(T('BG_DARK'), 0.7)}; border-radius: {S(6)}px;"
            f" padding: {S(2)}px {S(6)}px; border: none;"
        )
        # Re-apply face status (re-evaluates from current _pip_face_ok state)
        self._pip_on_face_detected(self._pip_face_ok)

    # ── UI construction ─────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("centralWidget")
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
        self._header_frame = QFrame()
        self._header_frame.setObjectName("header")
        self._header_frame.setFixedHeight(S(68))
        layout = QHBoxLayout(self._header_frame)
        layout.setContentsMargins(S(24), 0, S(24), 0)

        # Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("assets/logo.jpg")
        logo_label.setPixmap(logo_pixmap.scaled(S(40), S(40), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(logo_label)
        layout.addSpacing(S(12))

        # Title block
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        title = QLabel("Neuro-Gaze")
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

        return self._header_frame

    def _build_sidebar(self) -> QFrame:
        self._sidebar_frame = QFrame()
        self._sidebar_frame.setObjectName("sidebar")
        self._sidebar_frame.setFixedWidth(S(280))
        layout = QVBoxLayout(self._sidebar_frame)
        layout.setContentsMargins(S(12), S(24), S(12), S(24))
        layout.setSpacing(S(12))

        nav_items = [
            ("🏠  Dashboard", self.PAGE_DASHBOARD),
            ("🦽  Wheelchair Drive", self.PAGE_WHEELCHAIR),
            ("💡  Home Automation", self.PAGE_HOME),
            ("⌨️  Eye Keyboard", self.PAGE_KEYBOARD),
            ("💬  Quick Phrases", self.PAGE_PHRASES),
            ("🎮  Entertainment", self.PAGE_ENTERTAINMENT),
            ("⚙️  Settings", self.PAGE_SETTINGS),
            ("🎯  Calibration", self.PAGE_CALIBRATION),
            ("ℹ️  About", self.PAGE_ABOUT),
        ]
        self._nav_buttons: dict[int, DwellButton] = {}
        for label, page_idx in nav_items:
            btn = DwellButton(label, dwell_ms=600)
            btn.setObjectName("navBtn")
            btn.setCheckable(False)
            btn.set_active(False)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, p=page_idx: self._navigate(p))
            layout.addWidget(btn)
            self._nav_buttons[page_idx] = btn

        layout.addStretch(1)


        return self._sidebar_frame

    def _build_pages(self) -> QStackedWidget:
        self._pages = QStackedWidget()

        self._dashboard = DashboardWidget(self._config, self._tracker, self._speech)
        self._wheelchair = WheelchairWidget()
        self._home_automation = HomeAutomationWidget(self._speech)
        self._keyboard = KeyboardWidget(self._speech)
        self._phrases = PhrasesWidget(self._config, self._speech)
        self._settings = SettingsWidget(self._config, self._tracker, self._speech)
        self._calibration = CalibrationWizardWidget(self._config, self._tracker)
        self._about = AboutWidget()
        self._about.launch_tutorial_requested.connect(self._launch_tutorial)
        self._entertainment = EntertainmentWidget(tracker=self._tracker, speech=self._speech, audio=self._audio)

        self._pages.addWidget(self._dashboard)         # 0
        self._pages.addWidget(self._wheelchair)        # 1
        self._pages.addWidget(self._home_automation)   # 2
        self._pages.addWidget(self._keyboard)          # 3
        self._pages.addWidget(self._phrases)           # 4
        self._pages.addWidget(self._settings)          # 5
        self._pages.addWidget(self._about)             # 6
        self._pages.addWidget(self._calibration)       # 7
        self._pages.addWidget(self._entertainment)     # 8

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
            f"  background-color: {T('BG_PANEL')};"
            f"  border: 2px solid {T('ACCENT_HOVER')};"
            f"  border-radius: {S(14)}px;"
            f"}}"
        )

        # Drop-shadow effect
        shadow = QGraphicsDropShadowEffect(self._pip_container)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 153))  # rgba(0,0,0,0.6)
        self._pip_container.setGraphicsEffect(shadow)

        pip_layout = QVBoxLayout(self._pip_container)
        pip_layout.setContentsMargins(S(10), S(10), S(10), S(6))
        pip_layout.setSpacing(S(4))

        # Camera feed label
        self._pip_cam_label = QLabel()
        self._pip_cam_label.setFixedSize(FEED_W, FEED_H)
        self._pip_cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pip_cam_label.setStyleSheet(
            f"background: {T('BG_DARK')}; border-radius: 8px; border: none;"
        )
        pip_layout.addWidget(self._pip_cam_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Telemetry pill bar (EAR + face dot)
        telemetry_row = QHBoxLayout()
        telemetry_row.setContentsMargins(4, 0, 4, 0)
        telemetry_row.setSpacing(6)

        self._pip_face_dot = QLabel("●")
        self._pip_face_dot.setFixedSize(S(18), S(18))
        self._pip_face_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._pip_face_dot.setStyleSheet(
            f"color: {T('ACCENT_HOVER')}; font-size: {S(12)}px; border: none;"
        )
        telemetry_row.addWidget(self._pip_face_dot)

        self._pip_status_label = QLabel("FACE OK")
        self._pip_status_label.setStyleSheet(
            f"color: {T('ACCENT_HOVER')}; font-size: {S(10)}px; font-weight: 600; border: none;"
        )
        telemetry_row.addWidget(self._pip_status_label)

        telemetry_row.addStretch(1)

        self._pip_ear_label = QLabel("EAR: —")
        self._pip_ear_label.setStyleSheet(
            f"color: {T('TEXT_MUTED')}; font-size: 10px; font-weight: 600;"
            f" background: {hex_to_rgba(T('BG_DARK'), 0.7)}; border-radius: 6px;"
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
        self._emergency_bar = QWidget()
        self._emergency_bar.setFixedHeight(S(72))
        self._emergency_bar.setStyleSheet(
            f"background-color: {T('BG_PANEL')}; border-top: 1px solid {T('BORDER')};"
        )
        layout = QHBoxLayout(self._emergency_bar)
        layout.setContentsMargins(S(24), S(10), S(24), S(10))

        self._emergency_hint = QLabel("ESC — Stop Mouse  |  DANGER — Alert Others")
        self._emergency_hint.setStyleSheet(f"color: {T('TEXT_MUTED')}; font-size: {S(13)}px;")
        layout.addWidget(self._emergency_hint, 1)

        self._btn_alert = QPushButton("🚨  PATIENT EMERGENCY ALERT")
        self._btn_alert.setObjectName("alertBtn")
        self._btn_alert.setFixedHeight(S(52))
        self._btn_alert.setStyleSheet(f"""
            QPushButton#alertBtn {{
                background-color: {T("ALERT_BG")};
                color: white;
                border: 2px solid {T("ALERT_BORDER")};
                border-radius: 8px;
                padding: 10px 30px;
                font-size: 16px;
                font-weight: 900;
                letter-spacing: 1px;
            }}
            QPushButton#alertBtn:hover {{
                background-color: {T("ALERT_HOVER")};
                border: 2px solid {T("ALERT_BG")};
            }}
        """)
        self._btn_alert.clicked.connect(self._trigger_patient_alert)
        layout.addWidget(self._btn_alert)

        layout.addSpacing(15)
        
        self._btn_ping = QPushButton("🔔  PING CAREGIVER")
        self._btn_ping.setFixedHeight(S(52))
        self._btn_ping.setStyleSheet(f"""
            QPushButton {{
                background-color: {T("BG_PANEL")};
                color: {T("TEXT_PRIMARY")};
                border: 2px solid {T("ACCENT")};
                border-radius: 8px;
                padding: 10px 30px;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: {T("ACCENT")};
                color: {T("KEY_HOVER_TEXT")};
            }}
        """)
        self._btn_ping.clicked.connect(self._ping_caregiver)
        layout.addWidget(self._btn_ping)

        layout.addSpacing(15)

        self._btn_emergency = QPushButton("🛑  EMERGENCY STOP")
        self._btn_emergency.setObjectName("emergencyBtn")
        self._btn_emergency.setFixedHeight(S(52))
        self._btn_emergency.setStyleSheet(f"""
            QPushButton#emergencyBtn {{
                background-color: {T("DANGER")};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 30px;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QPushButton#emergencyBtn:hover {{
                background-color: {T("EMERGENCY_HOVER")};
            }}
        """)
        self._btn_emergency.clicked.connect(self._emergency_stop)
        layout.addWidget(self._btn_emergency)

        return self._emergency_bar

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
            btn.set_active(idx == page_idx)

        # Toggle PiP visibility (guard needed: first _navigate call
        # happens inside _build_pages before _build_pip_overlay runs)
        if hasattr(self, '_pip_container'):
            if page_idx in (self.PAGE_DASHBOARD, self.PAGE_ENTERTAINMENT, self.PAGE_SETTINGS):
                self._pip_container.hide()
            else:
                self._pip_container.show()
                self._pip_container.raise_()  # ensure it's on top
                self._reposition_pip()

        log.debug("Navigated to page %d", page_idx)

    # ── tutorial ──────────────────────────────────────────────────

    def _launch_tutorial(self) -> None:
        steps = [
            {
                "targets": [self._header_frame],
                "message": "Monitors critical tracking telemetry in real time. Ensure your face is detected and the camera indicates ACTIVE before attempting navigation or environmental control.",
                "on_enter": lambda: self._navigate(self.PAGE_DASHBOARD)
            },
            {
                "targets": [self._nav_buttons[self.PAGE_WHEELCHAIR], self._wheelchair._title],
                "message": "Dwell your gaze on any directional card to move. The central STOP button triggers immediately upon gaze entry with zero delay. Automated ultrasonic sonar enforces an emergency stop if obstacles approach within 45 cm.",
                "on_enter": lambda: self._navigate(self.PAGE_WHEELCHAIR)
            },
            {
                "targets": [self._nav_buttons[self.PAGE_HOME], getattr(self._home_automation, '_title', self._nav_buttons[self.PAGE_HOME])],
                "message": "Manage room appliances using dedicated ON and OFF buttons. Fixate your gaze for 500 ms to trigger the local relay via the secondary ESP32 node without cloud lag.",
                "on_enter": lambda: self._navigate(self.PAGE_HOME)
            },
            {
                "targets": [self._nav_buttons[self.PAGE_KEYBOARD], getattr(self._keyboard, '_title', self._nav_buttons[self.PAGE_KEYBOARD])],
                "message": "Gives locked-in patients an immediate voice. Trigger pre-saved essential phrases with a single blink or compose custom sentences with real-time text-to-speech voicing.",
                "on_enter": lambda: self._navigate(self.PAGE_KEYBOARD)
            },
            {
                "targets": [self._emergency_bar],
                "message": "Use 'Ping Caregiver' for routine assistance. 'Emergency Alert' sounds an acoustic siren locally over laptop speakers. Pressing the physical ESC key instantly halts all wheelchair drive motors.",
                "on_enter": None
            }
        ]
        self._tutorial.set_steps(steps)
        self._tutorial.start()

    # ── emergency stop ────────────────────────────────────────────

    def _emergency_stop(self) -> None:
        self._tracker.emergency_stop()
        self._dashboard.on_external_stop()
        self._pill_tracking.set_ok(False, "STOPPED")
        
        if hasattr(self, "_emergency_flash_timer") and self._emergency_flash_timer.isActive():
            self._emergency_flash_timer.stop()
            self.centralWidget().setStyleSheet("")
            
        log.warning("Emergency stop triggered from MainWindow")

    def _flash_emergency_border(self) -> None:
        self._emergency_border_visible = not self._emergency_border_visible
        if self._emergency_border_visible:
            self.centralWidget().setStyleSheet("QWidget#centralWidget { border: 8px solid #FF4757; }")
        else:
            self.centralWidget().setStyleSheet("")

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
                f"  background-color: {T('BG_PANEL')};"
                f"  border: 2px solid {T('ACCENT_HOVER')};"
                f"  border-radius: 14px;"
                f"}}"
            )
            self._pip_face_dot.setStyleSheet(
                f"color: {T('ACCENT_HOVER')}; font-size: 12px; border: none;"
            )
            self._pip_status_label.setText("FACE OK")
            self._pip_status_label.setStyleSheet(
                f"color: {T('ACCENT_HOVER')}; font-size: 10px; font-weight: 600; border: none;"
            )
        else:
            self._pip_face_dot.setStyleSheet(
                f"color: {T('DANGER')}; font-size: {S(12)}px; border: none;"
            )
            self._pip_status_label.setText("FACE LOST")
            self._pip_status_label.setStyleSheet(
                f"color: {T('DANGER')}; font-size: {S(10)}px; font-weight: 600; border: none;"
            )
            if not self._pip_flash_timer.isActive():
                self._pip_border_visible = True
                self._pip_flash_timer.start()

    def _pip_flash_border(self) -> None:
        """Toggle the PiP border between red and transparent for a flashing alert."""
        self._pip_border_visible = not self._pip_border_visible
        border_color = T("DANGER") if self._pip_border_visible else "transparent"
        self._pip_container.setStyleSheet(
            f"QFrame#pipContainer {{"
            f"  background-color: {T('BG_PANEL')};"
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
        session_logger.log_event("EMERGENCY", "Patient Emergency Alert Triggered")
        
        webhook_url = self._config.get("webhook_url", "")
        if webhook_url:
            CaregiverNotifier.send_webhook(webhook_url, "🚨 PATIENT HAS TRIGGERED THE EMERGENCY ALERT! Assistance required immediately.", is_emergency=True)

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
        
        self._emergency_flash_timer.start()
        self._speech.speak("Emergency! Patient requires immediate attention!")
        QMessageBox.critical(self, "EMERGENCY ALERT", "PATIENT HAS TRIGGERED THE EMERGENCY ALERT!\nPress ESC to silence the alarm.")

    def _on_tracking_error(self, message: str) -> None:
        self._pill_camera.set_ok(False, "Error")
        QMessageBox.critical(self, "Tracking Error", message)

    def _ping_caregiver(self) -> None:
        log.info("Caregiver ping triggered")
        session_logger.log_event("PING", "Caregiver ping triggered")
        
        # Local Audio Chime
        import threading
        import winsound
        def _play_chime():
            winsound.Beep(600, 200)
            winsound.Beep(800, 300)
        threading.Thread(target=_play_chime, daemon=True).start()
        
        self._speech.speak("Caregiver needed. Patient is requesting assistance.")
        
        webhook_url = self._config.get("webhook_url", "")
        if webhook_url:
            CaregiverNotifier.send_webhook(webhook_url, "The patient has requested non-emergency assistance.", is_emergency=False)

    # ── cleanup ──────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        log.info("Application closing")
        session_logger.end_session()
        self._tracker.stop_tracking()
        self._tracker.stop_thread()
        self._tracker.wait(3000)
        if hasattr(self, '_audio') and self._audio:
            self._audio.close()
        self._config.save()
        event.accept()
