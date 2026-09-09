"""
ui/phrases.py
--------------
Quick Phrases page.

Displays large, accessible buttons for pre-configured phrases.
Head movement positions the cursor; blink triggers the button click
via PyAutoGUI (same mechanism as the keyboard).

All colour tokens come from ``ui.theme`` for live Dark/Light switching.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QLineEdit,
)

from core.speech_engine import SpeechEngine
from ui.components import DwellButton
from ui.theme import T, S, theme_manager
from utils.config import Config
from utils.logger import get_logger

log = get_logger(__name__)


def _phrase_style() -> str:
    return f"""
QPushButton {{
    background-color: {T("BG_PHRASE_BTN")};
    color: {T("TEXT_PRIMARY")};
    border: 2px solid {T("PHRASE_BORDER")};
    border-radius: {S(12)}px;
    font-size: {S(17)}px;
    font-weight: 600;
    padding: {S(18)}px {S(12)}px;
    min-height: {S(70)}px;
    text-align: center;
}}
QPushButton:hover {{
    background-color: {T("ACCENT")};
    color: {T("KEY_HOVER_TEXT")};
    border: 2px solid {T("ACCENT")};
    font-weight: 800;
}}
QPushButton:pressed {{
    background-color: {T("ACCENT_PRESSED")};
}}
"""

def _pain_style() -> str:
    return f"""
QPushButton {{
    background-color: {T("BG_PANEL")};
    color: {T("DANGER")};
    border: 1px solid {T("DANGER")};
    border-radius: {S(20)}px;
    font-size: {S(16)}px;
    font-weight: 800;
    min-width: {S(40)}px;
    min-height: {S(40)}px;
}}
QPushButton:hover {{
    background-color: {T("DANGER")};
    color: white;
}}
"""

def _delete_style() -> str:
    return f"""
QPushButton {{
    background-color: transparent;
    color: {T("DANGER")};
    border: none;
    font-size: {S(24)}px;
    font-weight: 800;
}}
QPushButton:hover {{
    color: {T("TEXT_PRIMARY")};
}}
"""


class PhrasesWidget(QWidget):
    """Quick Phrases page."""

    def __init__(self, config: Config, speech: SpeechEngine, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._speech = speech
        self._edit_mode = False
        self._phrase_buttons: list[QPushButton] = []
        self._delete_buttons: list[QPushButton] = []
        self._pain_buttons: list[QPushButton] = []
        self._build_ui()
        self._apply_theme()
        theme_manager().theme_changed.connect(self._apply_theme)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(S(32), S(24), S(32), S(24))
        outer.setSpacing(S(16))

        # Header Row (Title + Edit Mode Toggle + Add)
        header_ly = QHBoxLayout()
        self._title = QLabel("💬  Quick Phrases")
        header_ly.addWidget(self._title)
        header_ly.addStretch(1)

        self._btn_add = DwellButton("➕  Add Phrase", dwell_ms=1000)
        self._btn_add.clicked.connect(self._add_phrase)
        self._btn_add.setVisible(False)
        header_ly.addWidget(self._btn_add)

        self._btn_edit = DwellButton("✏️  Edit Mode", dwell_ms=1000)
        self._btn_edit.clicked.connect(self._toggle_edit_mode)
        header_ly.addWidget(self._btn_edit)

        outer.addLayout(header_ly)

        self._hint_lbl = QLabel(
            "Hover over a phrase button with head movement, then blink to speak it."
        )
        outer.addWidget(self._hint_lbl)

        # Speaking indicator
        self._speak_lbl = QLabel("")
        outer.addWidget(self._speak_lbl)
        self._speech.speaking_started.connect(
            lambda: self._speak_lbl.setText("🔊  Speaking…")
        )
        self._speech.speaking_finished.connect(
            lambda: self._speak_lbl.setText("")
        )

        # Phrase grid container
        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(S(12))
        outer.addWidget(self._grid_container, 1)

        # Pain Scale
        pain_ly = QHBoxLayout()
        pain_ly.setSpacing(S(8))
        self._pain_lbl = QLabel("Pain Scale:")
        pain_ly.addWidget(self._pain_lbl)
        
        for i in range(1, 11):
            btn = QPushButton(str(i))
            btn.clicked.connect(lambda checked=False, lvl=i: self._speak_pain(lvl))
            self._pain_buttons.append(btn)
            pain_ly.addWidget(btn)
            
        pain_ly.addStretch(1)
        outer.addLayout(pain_ly)

        # Last spoken label
        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.Shape.HLine)
        outer.addWidget(self._sep)

        row_last = QHBoxLayout()
        self._last_prefix = QLabel("Last spoken:")
        row_last.addWidget(self._last_prefix)
        self._last_lbl = QLabel("—")
        row_last.addWidget(self._last_lbl)
        row_last.addStretch(1)
        outer.addLayout(row_last)
        
        self._rebuild_grid()

    def _apply_theme(self) -> None:
        self._title.setStyleSheet(
            f"color:{T('TEXT_PRIMARY')}; font-size:{S(20)}px; font-weight:700;"
        )
        self._hint_lbl.setStyleSheet(f"color:{T('TEXT_MUTED')}; font-size:{S(12)}px;")
        self._speak_lbl.setStyleSheet(
            f"color:{T('ACCENT')}; font-size:{S(13)}px; font-weight:700;"
        )
        self._sep.setStyleSheet(f"color:{T('BORDER_SOLID')};")
        self._last_prefix.setStyleSheet(f"color:{T('TEXT_MUTED')};")
        self._last_lbl.setStyleSheet(f"color:{T('ACCENT')}; font-weight:600;")
        self._pain_lbl.setStyleSheet(f"color:{T('TEXT_PRIMARY')}; font-size:{S(14)}px; font-weight:600;")
        
        ps = _phrase_style()
        for btn in self._phrase_buttons:
            btn.setStyleSheet(ps)
            
        ds = _delete_style()
        for btn in self._delete_buttons:
            btn.setStyleSheet(ds)
            
        pns = _pain_style()
        for btn in self._pain_buttons:
            btn.setStyleSheet(pns)

    def _rebuild_grid(self) -> None:
        # Clear existing
        while self._grid_layout.count():
            child = self._grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self._phrase_buttons.clear()
        self._delete_buttons.clear()

        phrases: list[str] = self._config.get("phrases", [])
        
        for i, phrase in enumerate(phrases):
            w = QWidget()
            ly = QHBoxLayout(w)
            ly.setContentsMargins(0,0,0,0)
            ly.setSpacing(S(8))
            
            btn = QPushButton(phrase)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.clicked.connect(lambda checked=False, p=phrase: self._speak(p))
            self._phrase_buttons.append(btn)
            ly.addWidget(btn, 1)
            
            if self._edit_mode:
                del_btn = QPushButton("✕")
                del_btn.setFixedSize(S(40), S(40))
                del_btn.clicked.connect(lambda checked=False, p=phrase: self._delete_phrase(p))
                self._delete_buttons.append(del_btn)
                ly.addWidget(del_btn, 0)
                
            row, col = divmod(i, 2)
            self._grid_layout.addWidget(w, row, col)
            
        self._apply_theme()

    def _toggle_edit_mode(self) -> None:
        self._edit_mode = not self._edit_mode
        if self._edit_mode:
            self._btn_edit.setText("✓  Done Editing")
            self._btn_add.setVisible(True)
        else:
            self._btn_edit.setText("✏️  Edit Mode")
            self._btn_add.setVisible(False)
        self._rebuild_grid()

    def _add_phrase(self) -> None:
        text, ok = QInputDialog.getText(self, "Add Phrase", "Enter new phrase:", QLineEdit.EchoMode.Normal, "")
        if ok and text.strip():
            phrases = self._config.get("phrases", [])
            phrases.append(text.strip())
            self._config.set("phrases", phrases)
            self._config.save()
            self._rebuild_grid()

    def _delete_phrase(self, phrase: str) -> None:
        phrases = self._config.get("phrases", [])
        if phrase in phrases:
            phrases.remove(phrase)
            self._config.set("phrases", phrases)
            self._config.save()
            self._rebuild_grid()

    def _speak_pain(self, level: int) -> None:
        phrase = f"My pain level is {level} out of 10."
        self._speak(phrase)

    def _speak(self, phrase: str) -> None:
        log.info("Quick phrase: %r", phrase)
        self._last_lbl.setText(f'"{phrase}"')
        self._speech.speak(phrase)
