"""
ui/wheelchair.py
-----------------
Implementation for ESP32-based wheelchair interface.
Uses ui.theme for all styling.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import json
import threading
import urllib.request
import urllib.error

from ui.components import DwellButton
from ui.theme import T, S, theme_manager
from utils.logger import get_logger

log = get_logger(__name__)


class DriveButton(DwellButton):
    """Directional pad button for the wheelchair interface."""

    gaze_left = Signal()
    gaze_entered = Signal()

    def __init__(self, text: str, is_stop: bool = False, parent=None) -> None:
        # STOP gets 0ms dwell, others get 500ms
        dwell = 0 if is_stop else 500
        super().__init__(text, dwell_ms=dwell, parent=parent)
        self.is_stop = is_stop
        self.setMinimumHeight(S(100))
        self._apply_style()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.gaze_entered.emit()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.gaze_left.emit()

    def _apply_style(self):
        bg = T("DANGER") if self.is_stop else T("BG_KEY")
        hover_bg = T("EMERGENCY_HOVER") if self.is_stop else T("ACCENT")
        color = "white" if self.is_stop else T("TEXT_PRIMARY")
        
        self.setStyleSheet(f"""
            DriveButton {{
                background-color: {bg};
                color: {color};
                border: 2px solid {T("BORDER_SOLID")};
                border-radius: {S(12)}px;
                font-size: {S(18)}px;
                font-weight: 800;
            }}
            DriveButton:hover {{
                background-color: {hover_bg};
                color: {T("KEY_HOVER_TEXT")};
                border: 2px solid {hover_bg};
            }}
        """)


class WheelchairWidget(QWidget):
    telemetry_updated = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._buttons = []
        self._fails = 0
        
        self._stop_timer = QTimer(self)
        self._stop_timer.setSingleShot(True)
        self._stop_timer.setInterval(250)
        self._stop_timer.timeout.connect(lambda: self._drive("🛑 STOP"))
        
        self._build_ui()
        self._apply_theme()
        theme_manager().theme_changed.connect(self._apply_theme)
        
        self.telemetry_updated.connect(self._on_telemetry_updated)
        self._polling_timer = QTimer(self)
        self._polling_timer.setInterval(200)
        self._polling_timer.timeout.connect(self._poll_telemetry)
        self._polling_timer.start()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(S(32), S(24), S(32), S(24))
        outer.setSpacing(S(16))

        self._title = QLabel("🦽  Wheelchair Drive")
        outer.addWidget(self._title)

        self._hint = QLabel("Hover over a direction to drive. The chair stops automatically when you look away.")
        outer.addWidget(self._hint)

        # Telemetry Header
        self._header_lbl = QLabel("Front: -- cm | Rear: -- cm")
        self._header_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self._header_lbl)

        # Drive pad
        grid = QGridLayout()
        grid.setSpacing(S(12))

        btn_fwd = self._make_btn("⬆️ FORWARD")
        btn_rev = self._make_btn("⬇️ BACKWARD")
        btn_left = self._make_btn("⬅️ LEFT")
        btn_right = self._make_btn("➡️ RIGHT")
        btn_stop = self._make_btn("🛑 STOP", is_stop=True)

        grid.addWidget(btn_fwd, 0, 1)
        grid.addWidget(btn_left, 1, 0)
        grid.addWidget(btn_stop, 1, 1)
        grid.addWidget(btn_right, 1, 2)
        grid.addWidget(btn_rev, 2, 1)

        outer.addLayout(grid, 1)

        self._status = QLabel("Status: Idle")
        outer.addWidget(self._status, alignment=Qt.AlignmentFlag.AlignCenter)

    def _make_btn(self, label: str, is_stop: bool = False) -> DriveButton:
        btn = DriveButton(label, is_stop)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        btn.clicked.connect(lambda checked, l=label: self._drive(l))
        btn.gaze_entered.connect(self._stop_timer.stop)
        btn.gaze_left.connect(self._stop_timer.start)
        self._buttons.append(btn)
        return btn

    def _drive(self, direction: str) -> None:
        cmd_map = {
            "⬆️ FORWARD": "F",
            "⬇️ BACKWARD": "B",
            "⬅️ LEFT": "L",
            "➡️ RIGHT": "R",
            "🛑 STOP": "S"
        }
        cmd = cmd_map.get(direction, "S")
        log.info("Wheelchair drive: %s (Command: %s)", direction, cmd)

        if "STOP" in direction:
            self._status.setText("Status: Stopped")
        else:
            self._status.setText(f"Status: Driving {direction.split(' ')[1]}")

        def _send():
            try:
                req = urllib.request.Request(f"http://192.168.4.1/{cmd}", method="GET")
                with urllib.request.urlopen(req, timeout=0.5) as response:
                    pass
            except Exception as e:
                log.error("Drive command failed: %s", e)
                
        threading.Thread(target=_send, daemon=True).start()

    def _poll_telemetry(self) -> None:
        def _fetch():
            data = None
            try:
                req = urllib.request.Request("http://192.168.4.1/status", method="GET")
                with urllib.request.urlopen(req, timeout=0.15) as response:
                    if response.getcode() == 200:
                        data = json.loads(response.read().decode('utf-8'))
            except Exception:
                pass
            
            try:
                self.telemetry_updated.emit(data)
            except RuntimeError:
                # Widget was deleted during app shutdown
                pass
                
        threading.Thread(target=_fetch, daemon=True).start()

    def _on_telemetry_updated(self, data) -> None:
        if data is None:
            self._fails += 1
            if self._fails >= 3:
                self._header_lbl.setText("Front: -- cm | Rear: -- cm")
                self._header_lbl.setStyleSheet(f"color: {T('TEXT_MUTED')}; font-size: {S(16)}px; font-weight: 700; border: none;")
            return
            
        self._fails = 0
        front = data.get("front", 999)
        rear = data.get("rear", 999)
        
        front_txt = f"{front} cm" if front <= 400 else "Clear (>100 cm)"
        rear_txt = f"{rear} cm" if rear <= 400 else "Clear (>100 cm)"
        
        min_dist = min(front, rear)
        
        if min_dist <= 30:
            color = T("DANGER")
            self._header_lbl.setText(f"Front: {front_txt} | Rear: {rear_txt}   ⚠️ OBSTACLE CLOSE")
        elif min_dist <= 60:
            color = T("WARNING")
            self._header_lbl.setText(f"Front: {front_txt} | Rear: {rear_txt}")
        else:
            color = "#00B4D8"
            self._header_lbl.setText(f"Front: {front_txt} | Rear: {rear_txt}")
            
        self._header_lbl.setStyleSheet(f"color: {color}; font-size: {S(18)}px; font-weight: 800; border: 2px solid {color}; padding: {S(10)}px; border-radius: {S(8)}px;")

    def _apply_theme(self) -> None:
        self._title.setStyleSheet(
            f"color:{T('TEXT_PRIMARY')}; font-size:{S(20)}px; font-weight:700;"
        )
        self._hint.setStyleSheet(f"color:{T('TEXT_MUTED')}; font-size:{S(13)}px;")
        self._status.setStyleSheet(
            f"color:{T('ACCENT')}; font-size:{S(14)}px; font-weight:600;"
        )
        if self._fails >= 3:
            self._header_lbl.setStyleSheet(f"color: {T('TEXT_MUTED')}; font-size: {S(16)}px; font-weight: 700; border: none;")
            
        for btn in self._buttons:
            btn._apply_style()

