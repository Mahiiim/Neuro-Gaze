"""
ui/home_automation.py
----------------------
Placeholder implementation for ESP32-based home automation relays.
Uses ui.theme for all styling.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import threading
import urllib.request
import urllib.error

from PySide6.QtWidgets import QPushButton

from core.speech_engine import SpeechEngine
from ui.theme import T, S, theme_manager
from utils.logger import get_logger

log = get_logger(__name__)


class ApplianceButton(QPushButton):
    """Discrete appliance button triggered by a blink (mouse click)."""

    def __init__(self, text: str, is_on: bool, is_light: bool, parent=None) -> None:
        super().__init__(text, parent)
        self.is_on = is_on
        self.is_light = is_light
        self.setMinimumHeight(S(100))
        self._apply_style()

    def _apply_style(self):
        if self.is_on:
            color = "#2ED573" if self.is_light else "#00D2FF"  # Green or Cyan
        else:
            color = "#FF4757"  # Crimson

        self.setStyleSheet(f"""
            ApplianceButton {{
                background-color: {T("BG_KEY_SPECIAL")};
                color: {T("TEXT_PRIMARY")};
                border: 2px solid {color};
                border-radius: {S(12)}px;
                font-size: {S(18)}px;
                font-weight: 800;
            }}
            ApplianceButton:hover {{
                background-color: {color};
                color: {T("KEY_HOVER_TEXT")};
            }}
        """)


class HomeAutomationWidget(QWidget):
    def __init__(self, speech: SpeechEngine, parent=None) -> None:
        super().__init__(parent)
        self._speech = speech
        self._buttons = []
        self._build_ui()
        self._apply_theme()
        theme_manager().theme_changed.connect(self._apply_theme)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(S(32), S(24), S(32), S(24))
        outer.setSpacing(S(24))

        self._title = QLabel("💡  Home Automation (Simulated)")
        outer.addWidget(self._title)

        self._hint = QLabel("Hover and blink to toggle appliances in the room.")
        outer.addWidget(self._hint)

        row1 = QHBoxLayout()
        row1.setSpacing(S(16))
        row1.addWidget(self._make_btn("💡 Light ON", True, True))
        row1.addWidget(self._make_btn("🌑 Light OFF", False, True))

        row2 = QHBoxLayout()
        row2.setSpacing(S(16))
        row2.addWidget(self._make_btn("🌀 Fan ON", True, False))
        row2.addWidget(self._make_btn("⏹️ Fan OFF", False, False))

        outer.addLayout(row1)
        outer.addLayout(row2)
        outer.addStretch(1)

        self._status = QLabel("Relay Module: Awaiting commands")
        outer.addWidget(self._status, alignment=Qt.AlignmentFlag.AlignCenter)

    def _make_btn(self, label: str, is_on: bool, is_light: bool) -> ApplianceButton:
        btn = ApplianceButton(label, is_on, is_light)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        btn.clicked.connect(lambda checked, l=label: self._trigger_appliance(l))
        self._buttons.append(btn)
        return btn

    def _trigger_appliance(self, label: str) -> None:
        log.info("Appliance action: %s", label)
        
        spoken = label.replace("💡 ", "").replace("🌑 ", "").replace("🌀 ", "").replace("⏹️ ", "")
        self._speech.speak(f"{spoken}")
        self._status.setText(f"Last command: {label}")
        
        endpoint_map = {
            "💡 Light ON": "light_on",
            "🌑 Light OFF": "light_off",
            "🌀 Fan ON": "fan_on",
            "⏹️ Fan OFF": "fan_off"
        }
        
        action = endpoint_map.get(label, "")
        if action:
            url = f"http://192.168.4.1/home/{action}"
            def _fetch():
                try:
                    urllib.request.urlopen(url, timeout=2.0)
                except Exception:
                    pass
            threading.Thread(target=_fetch, daemon=True).start()

    def _apply_theme(self) -> None:
        self._title.setStyleSheet(
            f"color:{T('TEXT_PRIMARY')}; font-size:{S(20)}px; font-weight:700;"
        )
        self._hint.setStyleSheet(f"color:{T('TEXT_MUTED')}; font-size:{S(13)}px;")
        self._status.setStyleSheet(f"color:{T('WARNING')}; font-size:{S(12)}px;")
        for btn in self._buttons:
            btn._apply_style()
