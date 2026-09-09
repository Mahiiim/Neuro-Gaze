"""
ui/keyboard.py
---------------
Eye-controlled virtual keyboard page.

The keyboard is rendered as real QPushButtons in a grid.
Because the FaceTrackerWorker issues real PyAutoGUI clicks,
hovering the system cursor over any button and blinking will
trigger Qt's native button click — no special hit-testing needed.

Rows:
  1 2 3 4 5 6 7 8 9 0
  Q W E R T Y U I O P
  A S D F G H J K L BS
  Z X C V B N M . , CLR
  SPACE      ENTER   EXIT

All colour tokens come from ``ui.theme`` for live Dark/Light switching.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.speech_engine import SpeechEngine
from ui.theme import T, S, theme_manager
from utils.logger import get_logger
from utils.words import get_suggestions

log = get_logger(__name__)


def _key_style() -> str:
    return f"""
QPushButton {{
    background-color: {T("BG_KEY")};
    color: {T("TEXT_PRIMARY")};
    border: 1px solid {T("BORDER_SOLID")};
    border-radius: {S(8)}px;
    font-size: {S(16)}px;
    font-weight: 700;
    min-height: {S(56)}px;
    min-width: {S(54)}px;
}}
QPushButton:hover {{
    background-color: {T("ACCENT")};
    color: {T("KEY_HOVER_TEXT")};
    border: 2px solid {T("ACCENT")};
}}
QPushButton:pressed {{
    background-color: {T("ACCENT_PRESSED")};
}}
"""

def _special_style() -> str:
    return f"""
QPushButton {{
    background-color: {T("BG_KEY_SPECIAL")};
    color: {T("ACCENT")};
    border: 1px solid {T("ACCENT")};
    border-radius: {S(8)}px;
    font-size: {S(14)}px;
    font-weight: 700;
    min-height: {S(56)}px;
}}
QPushButton:hover {{
    background-color: {T("ACCENT")};
    color: {T("KEY_HOVER_TEXT")};
}}
"""

def _danger_style() -> str:
    return f"""
QPushButton {{
    background-color: {T("BG_KEY_DANGER")};
    color: {T("DANGER")};
    border: 1px solid {T("DANGER")};
    border-radius: {S(8)}px;
    font-size: {S(14)}px;
    font-weight: 700;
    min-height: {S(56)}px;
}}
QPushButton:hover {{
    background-color: {T("DANGER")};
    color: white;
}}
"""

def _success_style() -> str:
    return f"""
QPushButton {{
    background-color: {T("BG_KEY_SUCCESS")};
    color: {T("SUCCESS")};
    border: 1px solid {T("SUCCESS")};
    border-radius: {S(8)}px;
    font-size: {S(14)}px;
    font-weight: 700;
    min-height: {S(56)}px;
}}
QPushButton:hover {{
    background-color: {T("SUCCESS")};
    color: white;
}}
"""

def _suggestion_style() -> str:
    return f"""
QPushButton {{
    background-color: {T("BG_PANEL")};
    color: {T("ACCENT_HOVER")};
    border: 1px dashed {T("ACCENT_HOVER")};
    border-radius: {S(16)}px;
    font-size: {S(18)}px;
    font-weight: 600;
    padding: {S(8)}px {S(16)}px;
}}
QPushButton:hover {{
    background-color: {T("ACCENT")};
    color: {T("KEY_HOVER_TEXT")};
    border: 1px solid {T("ACCENT")};
}}
"""


class KeyboardWidget(QWidget):
    """Eye-controlled virtual keyboard page."""

    KB_ROWS = [
        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0"],
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L", "BS"],
        ["Z", "X", "C", "V", "B", "N", "M", ".", ",", "CLR"],
    ]
    BOTTOM_ROW = ["SPACE", "ENTER", "EXIT"]

    def __init__(self, speech: SpeechEngine, parent=None) -> None:
        super().__init__(parent)
        self._speech = speech
        self._text = ""
        self._current_word = ""
        self._key_buttons: list[QPushButton] = []
        self._sugg_buttons: list[QPushButton] = []
        self._build_ui()
        self._apply_theme()
        theme_manager().theme_changed.connect(self._apply_theme)

    # ── UI ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(S(24), S(20), S(24), S(20))
        outer.setSpacing(S(14))

        # Page title
        self._title = QLabel("⌨️  Eye-Controlled Keyboard")
        outer.addWidget(self._title)

        self._hint = QLabel("Hover cursor with head movement · Blink to select a key")
        outer.addWidget(self._hint)

        # Text display area
        self._text_frame = QFrame()
        self._text_frame.setFixedHeight(S(70))
        text_layout = QHBoxLayout(self._text_frame)
        text_layout.setContentsMargins(S(16), 0, S(16), 0)

        self._display = QLabel("| Start typing…")
        self._display.setWordWrap(False)
        self._display.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        text_layout.addWidget(self._display)
        outer.addWidget(self._text_frame)

        # Speaking status
        self._speak_lbl = QLabel("")
        outer.addWidget(self._speak_lbl)
        self._speech.speaking_started.connect(lambda: self._speak_lbl.setText("🔊 Speaking…"))
        self._speech.speaking_finished.connect(lambda: self._speak_lbl.setText(""))

        # Suggestions row
        self._suggestions_layout = QHBoxLayout()
        self._suggestions_layout.setSpacing(S(12))
        for _ in range(4):
            btn = QPushButton("")
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(self._on_suggestion_clicked)
            btn.setVisible(False)
            self._sugg_buttons.append(btn)
            self._suggestions_layout.addWidget(btn)
        
        outer.addLayout(self._suggestions_layout)
        outer.addSpacing(S(10))

        # Keyboard grid
        grid = QGridLayout()
        grid.setSpacing(S(6))

        for row_idx, row in enumerate(self.KB_ROWS):
            for col_idx, key in enumerate(row):
                btn = self._make_key_btn(key)
                grid.addWidget(btn, row_idx, col_idx)

        # Bottom row
        self._btn_space = QPushButton("SPACE")
        self._btn_space.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_space.clicked.connect(lambda: self._key_press("SPACE"))

        self._btn_enter = QPushButton("ENTER  🔊")
        self._btn_enter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_enter.clicked.connect(lambda: self._key_press("ENTER"))

        self._btn_exit = QPushButton("EXIT  ✕")
        self._btn_exit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_exit.clicked.connect(lambda: self._key_press("EXIT"))

        bottom_row_layout = QHBoxLayout()
        bottom_row_layout.setSpacing(S(6))
        bottom_row_layout.addWidget(self._btn_space, 5)
        bottom_row_layout.addWidget(self._btn_enter, 3)
        bottom_row_layout.addWidget(self._btn_exit, 2)

        outer.addLayout(grid)
        outer.addLayout(bottom_row_layout)
        outer.addStretch(1)

    def _make_key_btn(self, key: str) -> QPushButton:
        """Create one keyboard button."""
        btn = QPushButton(key)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(lambda checked=False, k=key: self._key_press(k))
        # Store reference + semantic type for theme refresh
        btn.setProperty("key_type", "danger" if key in ("BS", "CLR") else "normal")
        self._key_buttons.append(btn)
        return btn

    # ── theme application ────────────────────────────────────────

    def _apply_theme(self) -> None:
        self._title.setStyleSheet(
            f"color:{T('TEXT_PRIMARY')}; font-size:{S(20)}px; font-weight:700;"
        )
        self._hint.setStyleSheet(f"color:{T('TEXT_MUTED')}; font-size:{S(12)}px;")
        self._text_frame.setStyleSheet(
            f"background:{T('BG_CARD')}; border:2px solid {T('ACCENT')}; border-radius:{S(10)}px;"
        )
        self._display.setStyleSheet(
            f"color:{T('TEXT_PRIMARY')}; font-size:{S(22)}px; font-weight:500; "
            f"border:none; background:transparent;"
        )
        self._speak_lbl.setStyleSheet(
            f"color:{T('ACCENT')}; font-size:{S(12)}px; font-weight:600;"
        )
        # Key buttons
        ks = _key_style()
        ds = _danger_style()
        for btn in self._key_buttons:
            if btn.property("key_type") == "danger":
                btn.setStyleSheet(ds)
            else:
                btn.setStyleSheet(ks)
        # Bottom row
        self._btn_space.setStyleSheet(_special_style())
        self._btn_enter.setStyleSheet(_success_style())
        self._btn_exit.setStyleSheet(_danger_style())
        
        # Suggestions
        ss = _suggestion_style()
        for btn in self._sugg_buttons:
            btn.setStyleSheet(ss)

    # ── key handling ─────────────────────────────────────────────

    def _key_press(self, key: str) -> None:
        if key == "BS":
            self._text = self._text[:-1]
            if self._current_word:
                self._current_word = self._current_word[:-1]
            else:
                # Need to re-evaluate current word
                parts = self._text.split(" ")
                self._current_word = parts[-1] if parts else ""
        elif key == "CLR":
            self._text = ""
            self._current_word = ""
        elif key == "SPACE":
            self._text += " "
            self._current_word = ""
        elif key == "ENTER":
            if self._text.strip():
                self._speech.speak(self._text)
                log.info("Keyboard TTS: %r", self._text)
            self._current_word = ""
        elif key == "EXIT":
            # Navigate back to dashboard — find parent MainWindow
            self._go_to_dashboard()
        else:
            self._text += key
            # Since keyboard keys are uppercase:
            self._current_word += key.lower()

        self._update_display()
        self._update_suggestions()

    def _on_suggestion_clicked(self) -> None:
        btn = self.sender()
        if not isinstance(btn, QPushButton):
            return
        word = btn.text()
        
        # Replace the current incomplete word with the suggestion + space
        if self._current_word:
            # strip off the partial word
            self._text = self._text[:-len(self._current_word)]
        
        # Add the completed word (upper case for consistency or Title case)
        self._text += word.upper() + " "
        self._current_word = ""
        
        self._update_display()
        self._update_suggestions()

    def _update_suggestions(self) -> None:
        suggestions = get_suggestions(self._current_word, max_count=4)
        for i, btn in enumerate(self._sugg_buttons):
            if i < len(suggestions):
                btn.setText(suggestions[i])
                btn.setVisible(True)
            else:
                btn.setVisible(False)

    def _update_display(self) -> None:
        display_text = self._text if self._text else ""
        # Truncate from left if too long for display
        if len(display_text) > 40:
            display_text = "…" + display_text[-38:]
        self._display.setText(display_text + "|")

    def _go_to_dashboard(self) -> None:
        """Navigate to dashboard (page 0) via the parent MainWindow."""
        # Walk up the widget hierarchy to find MainWindow
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "_navigate"):
                parent._navigate(0)
                return
            parent = parent.parent()
