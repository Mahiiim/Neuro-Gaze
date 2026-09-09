"""
ui/settings.py
---------------
Settings page — all user-configurable parameters grouped by category.

Changes are applied immediately (hot-reloaded into the tracker) and
persisted to JSON when the user clicks Apply.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QCheckBox,
    QGroupBox,
    QLineEdit,
    QInputDialog,
    QMessageBox,
)

from core.face_tracker import FaceTrackerWorker
from core.camera import CameraManager
from core.speech_engine import SpeechEngine
from core.webhook import CaregiverNotifier
from ui.components import DwellButton
from ui.theme import T, S, theme_manager, set_theme, set_scale
from utils.config import Config
from utils.logger import get_logger

log = get_logger(__name__)


def _group_style() -> str:
    return f"""
QGroupBox {{
    color: {T("ACCENT")};
    font-size: {S(13)}px;
    font-weight: 700;
    border: 1px solid {T("BORDER_SOLID")};
    border-radius: {S(10)}px;
    margin-top: {S(14)}px;
    padding: {S(12)}px;
    background: {T("BG_CARD")};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 {S(10)}px;
    left: {S(12)}px;
}}
QLabel {{
    color: {T("TEXT_PRIMARY")};
    font-size: {S(12)}px;
}}
QDoubleSpinBox, QSpinBox, QComboBox {{
    background: {T("BG_PANEL")};
    color: {T("TEXT_PRIMARY")};
    border: 1px solid {T("BORDER_SOLID")};
    border-radius: {S(6)}px;
    padding: {S(4)}px {S(8)}px;
    min-height: {S(28)}px;
    font-size: {S(12)}px;
}}
QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {T("ACCENT")};
}}
QSlider::groove:horizontal {{
    height: {S(6)}px;
    background: {T("BORDER_SOLID")};
    border-radius: {S(3)}px;
}}
QSlider::handle:horizontal {{
    background: {T("ACCENT")};
    width: {S(16)}px;
    height: {S(16)}px;
    margin: -{S(5)}px 0;
    border-radius: {S(8)}px;
}}
QSlider::sub-page:horizontal {{
    background: {T("ACCENT")};
    border-radius: {S(3)}px;
}}
QCheckBox {{
    color: {T("TEXT_PRIMARY")};
    font-size: {S(12)}px;
}}
"""

def _btn_apply() -> str:
    return f"""
QPushButton {{
    background: {T("ACCENT")};
    color: {T("KEY_HOVER_TEXT")};
    border: none;
    border-radius: {S(8)}px;
    padding: {S(10)}px {S(32)}px;
    font-size: {S(13)}px;
    font-weight: 700;
}}
QPushButton:hover {{ background: {T("APPLY_HOVER")}; }}
"""

def _btn_reset() -> str:
    return f"""
QPushButton {{
    background: {T("BG_PANEL")};
    color: {T("DANGER")};
    border: 1px solid {T("DANGER")};
    border-radius: {S(8)}px;
    padding: {S(10)}px {S(32)}px;
    font-size: {S(13)}px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {T("DANGER")}; color: white; }}
"""


class SettingsWidget(QWidget):
    """Full settings page with grouped controls."""

    def __init__(
        self,
        config: Config,
        tracker: FaceTrackerWorker,
        speech: SpeechEngine,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._tracker = tracker
        self._speech = speech
        self._controls: dict[str, Any] = {}
        self._labels: list[QLabel] = []
        self._build_ui()
        self._apply_theme()
        theme_manager().theme_changed.connect(self._apply_theme)

    def _label(self, text: str) -> QLabel:
        """Helper to create a themed label and track it."""
        lbl = QLabel(text)
        self._labels.append(lbl)
        return lbl

    # ── UI construction ─────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scrollable area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)

        self._inner = QWidget()
        layout = QVBoxLayout(self._inner)
        layout.setContentsMargins(S(24), S(20), S(24), S(20))
        layout.setSpacing(S(16))

        self._title = QLabel("⚙️  Settings")
        layout.addWidget(self._title)

        layout.addWidget(self._build_profile_group())
        layout.addWidget(self._build_appearance_group())
        layout.addWidget(self._build_eye_group())
        layout.addWidget(self._build_camera_group())
        layout.addWidget(self._build_speech_group())
        layout.addWidget(self._build_interface_group())
        layout.addWidget(self._build_connectivity_group())
        layout.addStretch(1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        self._btn_apply_w = DwellButton("✓  Apply", dwell_ms=1000)
        self._btn_apply_w.clicked.connect(self._apply)

        self._btn_reset_w = DwellButton("↺  Reset to Defaults", dwell_ms=1000)
        self._btn_reset_w.clicked.connect(self._reset)

        self._status_lbl = QLabel("")

        btn_row.addWidget(self._btn_apply_w)
        btn_row.addWidget(self._btn_reset_w)
        btn_row.addWidget(self._status_lbl)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self._scroll.setWidget(self._inner)
        outer.addWidget(self._scroll)

    # ── groups ───────────────────────────────────────────────────

    def _build_profile_group(self) -> QGroupBox:
        grp = QGroupBox("👥  Patient Profiles")
        g = QGridLayout(grp)
        g.setSpacing(10)
        g.setColumnMinimumWidth(0, 180)

        g.addWidget(self._label("Active Profile"), 0, 0)
        
        row = QHBoxLayout()
        self._profile_combo = QComboBox()
        self._refresh_profile_combo()
        self._profile_combo.currentTextChanged.connect(self._on_profile_changed)
        row.addWidget(self._profile_combo, 1)
        
        btn_new = QPushButton("New Profile")
        btn_new.setStyleSheet(f"background: {T('BG_PANEL')}; color: {T('TEXT_PRIMARY')}; border: 1px solid {T('BORDER_SOLID')}; border-radius: {S(6)}px; padding: {S(4)}px {S(12)}px; font-size: {S(12)}px;")
        btn_new.clicked.connect(self._create_new_profile)
        row.addWidget(btn_new)
        
        g.addLayout(row, 0, 1)
        return grp

    def _refresh_profile_combo(self):
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        for p in Config.list_profiles():
            self._profile_combo.addItem(p)
        self._profile_combo.setCurrentText(self._config.profile_name)
        self._profile_combo.blockSignals(False)

    def _on_profile_changed(self, profile_name: str):
        if not profile_name or profile_name == self._config.profile_name:
            return
        self._config.switch_profile(profile_name)
        # Reload the whole settings UI to reflect new profile values
        self._reset(force_reload=True)
        self._status_lbl.setText(f"✓ Switched to profile: {profile_name}")
        self._status_lbl.setStyleSheet(f"color:{T('SUCCESS')}; font-size:{S(12)}px;")

    def _create_new_profile(self):
        text, ok = QInputDialog.getText(self, "New Profile", "Enter patient profile name (e.g. john):", QLineEdit.EchoMode.Normal, "")
        if ok and text.strip():
            name = text.strip().lower().replace(" ", "_")
            if name in Config.list_profiles():
                QMessageBox.warning(self, "Error", "Profile already exists.")
                return
            self._config.switch_profile(name)
            self._refresh_profile_combo()
            self._reset(force_reload=True)
            self._status_lbl.setText(f"✓ Created profile: {name}")
            self._status_lbl.setStyleSheet(f"color:{T('SUCCESS')}; font-size:{S(12)}px;")

    def _build_appearance_group(self) -> QGroupBox:
        grp = QGroupBox("🎨  Appearance")
        g = QGridLayout(grp)
        g.setSpacing(10)
        g.setColumnMinimumWidth(0, 180)

        g.addWidget(self._label("Theme"), 0, 0)
        theme_combo = QComboBox()
        theme_combo.addItem("Dark", "dark")
        theme_combo.addItem("Light", "light")
        theme_combo.addItem("High Contrast", "high_contrast")
        
        # Set initial value
        current_theme = self._config.get("theme", "dark")
        idx = theme_combo.findData(current_theme)
        if idx >= 0:
            theme_combo.setCurrentIndex(idx)
            
        # Live preview hook
        theme_combo.currentIndexChanged.connect(
            lambda i: set_theme(theme_combo.itemData(i))
        )
            
        g.addWidget(theme_combo, 0, 1)
        self._controls["theme"] = theme_combo

        g.addWidget(self._label("UI Scale"), 1, 0)
        scale_combo = QComboBox()
        scale_combo.addItem("Small", "small")
        scale_combo.addItem("Medium (Default)", "medium")
        scale_combo.addItem("Large", "large")
        scale_combo.addItem("Extra Large", "extra_large")
        
        current_scale = self._config.get("ui_scale", "medium")
        s_idx = scale_combo.findData(current_scale)
        if s_idx >= 0:
            scale_combo.setCurrentIndex(s_idx)
            
        # Live preview hook
        scale_combo.currentIndexChanged.connect(
            lambda i: set_scale(scale_combo.itemData(i))
        )
        
        g.addWidget(scale_combo, 1, 1)
        self._controls["ui_scale"] = scale_combo

        return grp

    def _build_eye_group(self) -> QGroupBox:
        grp = QGroupBox("👁️  Eye Tracking")
        g = QGridLayout(grp)
        g.setSpacing(10)
        g.setColumnMinimumWidth(0, 180)

        self._add_dspin(g, 0, "Blink Threshold", "blink_threshold", 0.05, 0.50, 3, 0.01)
        self._add_dspin(g, 1, "Click Cooldown (s)", "click_cooldown", 0.2, 5.0, 2, 0.1)
        self._add_dspin(g, 2, "Smoothing Min Alpha", "smoothing_alpha_min", 0.01, 0.50, 2, 0.01)
        self._add_dspin(g, 3, "Smoothing Max Alpha", "smoothing_alpha_max", 0.05, 1.0, 2, 0.05)
        self._add_dspin(g, 4, "Sensitivity X", "sensitivity_x", 0.5, 5.0, 2, 0.1)
        self._add_dspin(g, 5, "Sensitivity Y", "sensitivity_y", 0.5, 5.0, 2, 0.1)
        
        g.addWidget(self._label("Fatigue Mode (Extra Smoothing)"), 6, 0)
        chk_fm = QCheckBox()
        chk_fm.setChecked(self._config.get("fatigue_mode", False))
        g.addWidget(chk_fm, 6, 1)
        self._controls["fatigue_mode"] = chk_fm
        
        return grp

    def _build_camera_group(self) -> QGroupBox:
        grp = QGroupBox("📷  Camera")
        g = QGridLayout(grp)
        g.setSpacing(10)
        g.setColumnMinimumWidth(0, 180)

        # Camera index dropdown
        g.addWidget(self._label("Camera"), 0, 0)
        cam_combo = QComboBox()
        available = CameraManager.list_cameras()
        for idx in available:
            cam_combo.addItem(f"Camera {idx}", idx)
        current = self._config.get("camera_index", 0)
        cam_combo.setCurrentIndex(max(0, available.index(current)) if current in available else 0)
        g.addWidget(cam_combo, 0, 1)
        self._controls["camera_index"] = cam_combo

        self._add_spin(g, 1, "Width (px)", "camera_width", 320, 1920, 1)
        self._add_spin(g, 2, "Height (px)", "camera_height", 240, 1080, 1)
        return grp

    def _build_speech_group(self) -> QGroupBox:
        grp = QGroupBox("🔊  Speech")
        g = QGridLayout(grp)
        g.setSpacing(10)
        g.setColumnMinimumWidth(0, 180)

        g.addWidget(self._label("Voice"), 0, 0)
        voice_combo = QComboBox()
        for name in self._speech.voice_names:
            voice_combo.addItem(name)
        voice_idx = self._config.get("speech_voice_index", 0)
        voice_combo.setCurrentIndex(min(voice_idx, voice_combo.count() - 1))
        g.addWidget(voice_combo, 0, 1)
        self._controls["speech_voice_index"] = voice_combo

        self._add_spin(g, 1, "Speed (WPM)", "speech_rate", 80, 300, 10)
        self._add_dspin(g, 2, "Volume", "speech_volume", 0.0, 1.0, 2, 0.05)
        return grp

    def _build_interface_group(self) -> QGroupBox:
        grp = QGroupBox("🖥️  Interface")
        g = QGridLayout(grp)
        g.setSpacing(10)
        g.setColumnMinimumWidth(0, 180)

        g.addWidget(self._label("Show Landmarks"), 0, 0)
        chk_lm = QCheckBox()
        chk_lm.setChecked(self._config.get("show_landmarks", True))
        g.addWidget(chk_lm, 0, 1)
        self._controls["show_landmarks"] = chk_lm

        g.addWidget(self._label("Show Tracking Info"), 1, 0)
        chk_ti = QCheckBox()
        chk_ti.setChecked(self._config.get("show_tracking_info", True))
        g.addWidget(chk_ti, 1, 1)
        self._controls["show_tracking_info"] = chk_ti

        return grp

    def _build_connectivity_group(self) -> QGroupBox:
        grp = QGroupBox("🌐  Connectivity")
        g = QGridLayout(grp)
        g.setSpacing(10)
        g.setColumnMinimumWidth(0, 180)

        g.addWidget(self._label("Caregiver Webhook URL"), 0, 0)
        
        row = QHBoxLayout()
        webhook_edit = QLineEdit()
        webhook_edit.setPlaceholderText("https://discord.com/api/webhooks/...")
        webhook_edit.setText(self._config.get("webhook_url", ""))
        webhook_edit.setStyleSheet(f"background: {T('BG_PANEL')}; color: {T('TEXT_PRIMARY')}; border: 1px solid {T('BORDER_SOLID')}; border-radius: {S(6)}px; padding: {S(4)}px {S(8)}px; min-height: {S(28)}px; font-size: {S(12)}px;")
        self._controls["webhook_url"] = webhook_edit
        row.addWidget(webhook_edit, 1)

        btn_test = QPushButton("Test Ping")
        btn_test.setStyleSheet(f"background: {T('BG_PANEL')}; color: {T('TEXT_PRIMARY')}; border: 1px solid {T('BORDER_SOLID')}; border-radius: {S(6)}px; padding: {S(4)}px {S(12)}px; font-size: {S(12)}px;")
        btn_test.clicked.connect(lambda: CaregiverNotifier.send_webhook(webhook_edit.text(), "This is a test ping from Neuro-Gaze.", is_emergency=False))
        row.addWidget(btn_test)

        g.addLayout(row, 0, 1)

        return grp

    # ── helper builders ──────────────────────────────────────────

    def _add_dspin(
        self,
        grid: QGridLayout,
        row: int,
        label: str,
        key: str,
        min_val: float,
        max_val: float,
        decimals: int,
        step: float,
    ) -> None:
        grid.addWidget(self._label(label), row, 0)
        spin = QDoubleSpinBox()
        spin.setRange(min_val, max_val)
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        spin.setValue(self._config.get(key, 0.0))
        grid.addWidget(spin, row, 1)
        self._controls[key] = spin

    def _add_spin(
        self,
        grid: QGridLayout,
        row: int,
        label: str,
        key: str,
        min_val: int,
        max_val: int,
        step: int,
    ) -> None:
        grid.addWidget(self._label(label), row, 0)
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setSingleStep(step)
        spin.setValue(int(self._config.get(key, 0)))
        grid.addWidget(spin, row, 1)
        self._controls[key] = spin

    # ── apply / reset ────────────────────────────────────────────

    def _apply_theme(self) -> None:
        self._scroll.setStyleSheet(f"QScrollArea {{ border:none; background:{T('BG_DARK')}; }}")
        self._inner.setStyleSheet(_group_style())
        self._title.setStyleSheet(
            f"color:{T('TEXT_PRIMARY')}; font-size:{S(20)}px; font-weight:700; background:transparent;"
        )
        for lbl in self._labels:
            lbl.setStyleSheet(f"color:{T('TEXT_MUTED')}; font-size:{S(12)}px;")
        
        self._btn_apply_w.setStyleSheet(_btn_apply())
        self._btn_reset_w.setStyleSheet(_btn_reset())
        
        if "Settings saved" in self._status_lbl.text():
            self._status_lbl.setStyleSheet(f"color:{T('SUCCESS')}; font-size:{S(12)}px;")
        else:
            self._status_lbl.setStyleSheet(f"color:{T('WARNING')}; font-size:{S(12)}px;")

    def _apply(self) -> None:
        """Read all controls and push values into config + tracker."""
        for key, widget in self._controls.items():
            if isinstance(widget, (QDoubleSpinBox,)):
                self._config.set(key, widget.value())
            elif isinstance(widget, QSpinBox):
                self._config.set(key, widget.value())
            elif isinstance(widget, QComboBox):
                if key == "camera_index":
                    self._config.set(key, widget.currentData())
                elif key == "speech_voice_index":
                    self._config.set(key, widget.currentIndex())
                    self._speech.set_voice_by_index(widget.currentIndex())
                elif key == "theme":
                    self._config.set(key, widget.currentData())
                elif key == "ui_scale":
                    self._config.set(key, widget.currentData())
                else:
                    self._config.set(key, widget.currentText())
            elif isinstance(widget, QCheckBox):
                self._config.set(key, widget.isChecked())
            elif isinstance(widget, QLineEdit):
                self._config.set(key, widget.text().strip())

        # Apply speech settings immediately
        self._speech.set_rate(self._config.get("speech_rate", 150))
        self._speech.set_volume(self._config.get("speech_volume", 1.0))

        # Hot-reload tracker config
        self._tracker.update_config(self._config)
        self._tracker.set_show_landmarks(self._config.get("show_landmarks", True))

        self._config.save()
        self._status_lbl.setText("✓ Settings saved")
        self._status_lbl.setStyleSheet(f"color:{T('SUCCESS')}; font-size:{S(12)}px;")
        log.info("Settings applied and saved")

    def _reset(self, force_reload=False) -> None:
        if not force_reload:
            self._config.reset_to_defaults()
            
        # Reload controls with new values
        for key, widget in self._controls.items():
            val = self._config.get(key)
            if val is None:
                continue
            if isinstance(widget, QDoubleSpinBox):
                widget.setValue(float(val))
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(val))
            elif isinstance(widget, QCheckBox):
                widget.setChecked(bool(val))
            elif isinstance(widget, QComboBox):
                if key in ("theme", "ui_scale"):
                    idx = widget.findData(val)
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                    
        self._status_lbl.setText("↺ Defaults restored")
        self._status_lbl.setStyleSheet(f"color:{T('WARNING')}; font-size:{S(12)}px;")
        log.info("Settings reset to defaults")
