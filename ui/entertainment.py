"""
ui/entertainment.py
--------------------
Entertainment Hub for Neuro-Gaze (v2.1).

Architected precisely to the 4-Card Hub Specification.
Uses FadingStackedWidget for non-destructive view navigation.
"""

from __future__ import annotations

import random
import time
from typing import List, Tuple

from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl
import os
from PySide6.QtCore import Qt, QTimer, Signal, QVariantAnimation, QPoint, QPointF, QRectF, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QRadialGradient, QPixmap, QFont, QPainterPath
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.components import DwellButton, FadingStackedWidget
from ui.theme import T, S, hex_to_rgba, theme_manager
from utils.logger import get_logger
from core.lifecycle import ActivityLifecycleManager

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared View Header Bar
# ---------------------------------------------------------------------------

class _ViewHeader(QFrame):
    """
    Fixed top header required by the prompt:
    ⬅️ Back to Menu | Section Title | 🔄 Reset
    """
    back_clicked = Signal()
    reset_clicked = Signal()

    def __init__(self, title: str, show_reset: bool = True, parent=None):
        super().__init__(parent)
        self.setFixedHeight(S(68))
        self.setStyleSheet(f"background: {T('BG_PANEL')}; border-bottom: 1px solid {T('BORDER_SOLID')};")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(S(24), S(10), S(24), S(10))
        
        self._back_btn = DwellButton("⬅️  Back to Menu", dwell_ms=800)
        self._back_btn.setFixedHeight(S(48))
        self._back_btn.setFixedWidth(S(180))
        self._back_btn.setStyleSheet(
            f"DwellButton {{ background: {hex_to_rgba(T('BG_CARD'), 0.8)}; color: {T('TEXT_PRIMARY')}; "
            f"border: 1px solid {T('BORDER_SOLID')}; border-radius: {S(10)}px; font-weight: bold; font-size: {S(14)}px;}}"
            f"DwellButton:hover {{ border-color: {T('ACCENT')}; }}"
        )
        self._back_btn.clicked.connect(self.back_clicked)
        layout.addWidget(self._back_btn)
        
        layout.addStretch(1)
        
        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(f"font-size: {S(20)}px; font-weight: 800; color: {T('ACCENT')}; border: none;")
        layout.addWidget(self._title_lbl)
        
        layout.addStretch(1)
        
        if show_reset:
            self._reset_btn = DwellButton("🔄  Reset", dwell_ms=800)
            self._reset_btn.setFixedHeight(S(48))
            self._reset_btn.setFixedWidth(S(140))
            self._reset_btn.setStyleSheet(
                f"DwellButton {{ background: {hex_to_rgba(T('BG_CARD'), 0.8)}; color: {T('TEXT_PRIMARY')}; "
                f"border: 1px solid {T('BORDER_SOLID')}; border-radius: {S(10)}px; font-weight: bold; font-size: {S(14)}px;}}"
                f"DwellButton:hover {{ border-color: {T('ACCENT')}; }}"
            )
            self._reset_btn.clicked.connect(self.reset_clicked)
            layout.addWidget(self._reset_btn)
        else:
            spacer = QWidget()
            spacer.setFixedWidth(S(140))
            spacer.setStyleSheet("border: none; background: transparent;")
            layout.addWidget(spacer)


# ---------------------------------------------------------------------------
# Core Structure: 4 Main Category Cards (MainMenu)
# ---------------------------------------------------------------------------

class _MainCategoryCard(QFrame):
    clicked = Signal()

    def __init__(self, title: str, icon: str, desc: str, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(S(180))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(S(32), S(32), S(32), S(32))
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet(
            f"font-family: 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif; "
            f"font-size: {S(56)}px; border: none; background: transparent; padding: 0; margin: 0;"
        )
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_icon)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: {S(22)}px; font-weight: 900; color: {color}; border: none; background: transparent;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet(f"font-size: {S(13)}px; color: {T('TEXT_MUTED')}; border: none; background: transparent;")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc)
        
        self._dwell = DwellButton("▶ Enter", dwell_ms=700)
        self._dwell.setFixedHeight(S(44))
        self._dwell.setStyleSheet(
            f"DwellButton {{ background: {hex_to_rgba(color, 0.15)}; color: {color}; border: 1px solid {color}; border-radius: {S(12)}px; font-size: {S(14)}px; font-weight: bold; }}"
        )
        self._dwell.clicked.connect(self.clicked)
        layout.addWidget(self._dwell)

        self.setStyleSheet(
            f"QFrame {{ background: {T('BG_CARD')}; border: 2px solid {hex_to_rgba(color, 0.3)}; border-radius: {S(20)}px; }}"
            f"QFrame:hover {{ border: 2px solid {color}; background: {hex_to_rgba(color, 0.05)}; }}"
        )

class _MainMenu(QWidget):
    """The 2x2 grid root menu."""
    nav_games = Signal()
    nav_health = Signal()
    nav_music = Signal()
    nav_studio = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(S(40), S(30), S(40), S(40))

        header = QLabel("🎮 ENTERTAINMENT HUB")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"font-size: {S(32)}px; font-weight: 900; color: {T('TEXT_PRIMARY')}; letter-spacing: 2px;")
        layout.addWidget(header)

        sub = QLabel("Select an activity below using gaze, blink, or mouse click")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"font-size: {S(16)}px; color: {T('TEXT_MUTED')}; margin-bottom: {S(24)}px;")
        layout.addWidget(sub)

        grid = QGridLayout()
        grid.setSpacing(S(24))
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        c1 = _MainCategoryCard("1. GAMES & LEISURE", "🎮", "Memory Match, Tic-Tac-Toe, Gaze Target, Bubble Pop, Simon", "#00D2FF")
        c1.clicked.connect(self.nav_games)
        grid.addWidget(c1, 0, 0)

        c2 = _MainCategoryCard("2. HEALTH ACTIVITIES", "🧘", "Paced Breathing (4-4-6 / Box), Facial Muscle Relaxation Guide", "#10B981")
        c2.clicked.connect(self.nav_health)
        grid.addWidget(c2, 0, 1)

        c3 = _MainCategoryCard("3. MUSIC & SOUND", "🎵", "Ambient Sound Mixer (Rain, Ocean), Pentatonic Chimes & Harp", "#8B5CF6")
        c3.clicked.connect(self.nav_music)
        grid.addWidget(c3, 1, 0)

        c4 = _MainCategoryCard("4. CREATIVE STUDIO", "🎨", "Eye-Art Neon Drawing Canvas, Palette Picker & Export", "#F59E0B")
        c4.clicked.connect(self.nav_studio)
        grid.addWidget(c4, 1, 1)

        layout.addLayout(grid)


# ---------------------------------------------------------------------------
# Section 1: Games Sub-Menu & Games
# ---------------------------------------------------------------------------

class _GameTile(QFrame):
    clicked = Signal()
    def __init__(self, title, desc, icon, color, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(S(160))
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet(
            f"font-family: 'Segoe UI Emoji', 'Apple Color Emoji', 'Noto Color Emoji', sans-serif; "
            f"font-size: {S(36)}px; background: transparent; border: none; padding: 0; margin: 0;"
        )
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_icon)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: {S(16)}px; font-weight: bold; color: {color}; background: transparent; border: none;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)

        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet(f"font-size: {S(12)}px; color: {T('TEXT_MUTED')}; background: transparent; border: none;")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_desc)

        btn = DwellButton("Play", dwell_ms=600)
        btn.setFixedHeight(S(36))
        btn.setStyleSheet(f"DwellButton {{ background: {hex_to_rgba(color, 0.2)}; color: {color}; border-radius: {S(8)}px; font-weight: bold; }}")
        btn.clicked.connect(self.clicked)
        layout.addWidget(btn)

        self.setStyleSheet(
            f"QFrame {{ background: {T('BG_CARD')}; border: 1px solid {hex_to_rgba(color, 0.4)}; border-radius: {S(16)}px; }}"
            f"QFrame:hover {{ border: 2px solid {color}; }}"
        )


class _GamesMenu(QWidget):
    back_clicked = Signal()
    launch_game = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.header = _ViewHeader("Games & Leisure", show_reset=False)
        self.header.back_clicked.connect(self.back_clicked)
        layout.addWidget(self.header)

        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(S(40), S(20), S(40), S(40))
        grid.setSpacing(S(20))

        games = [
            ("Memory Match", "Flip cards and find pairs", "\U0001f0cf", "#7C3AED", 5),
            ("Tic-Tac-Toe", "Offline AI opponent", "\u2b55", "#06B6D4", 6),
            ("Gaze Target", "Hit shrinking targets", "\U0001f3af", "#F97316", 7),
            ("Zen Bubble Pop", "Pop floating bubbles", "\U0001f9e7", "#10B981", 8),
            ("Simon Sequence", "Repeat patterns", "\U0001f514", "#F59E0B", 9)
        ]

        for i, (t, d, ic, c, idx) in enumerate(games):
            tile = _GameTile(t, d, ic, c)
            tile.clicked.connect(lambda checked=False, x=idx: self.launch_game.emit(x))
            grid.addWidget(tile, i // 3, i % 3)
            
        layout.addWidget(grid_w, 1)


# Memory Match
class _GazeFocusCard(QPushButton):
    activate = Signal()
    def __init__(self, symbol, parent=None):
        super().__init__("?", parent)
        self._symbol = symbol
        self._flipped = False
        self._matched = False

        self.clicked.connect(self.activate.emit)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._refresh()

    def flip_up(self):
        self._flipped = True
        self._refresh()

    def flip_down(self):
        self._flipped = False
        self._refresh()

    def mark_matched(self, is_ai=False):
        self._matched = True
        self._is_ai_match = is_ai
        self._refresh()

    def _refresh(self):
        font_style = f"font-family: 'Segoe UI Emoji', sans-serif; font-size: {S(32)}px;"
        if self._matched:
            self.setText(self._symbol)
            if hasattr(self, '_is_ai_match') and self._is_ai_match:
                self.setStyleSheet(f"QPushButton {{ background: {hex_to_rgba('#FF6B6B', 0.2)}; color: #FF6B6B; border: 2px solid #FF6B6B; border-radius: {S(12)}px; {font_style} }}")
            else:
                self.setStyleSheet(f"QPushButton {{ background: {hex_to_rgba('#2ED573', 0.2)}; color: #2ED573; border: 2px solid #2ED573; border-radius: {S(12)}px; {font_style} }}")
        elif self._flipped:
            self.setText(self._symbol)
            self.setStyleSheet(f"QPushButton {{ background: {hex_to_rgba(T('ACCENT'), 0.2)}; color: {T('ACCENT')}; border: 2px solid {T('ACCENT')}; border-radius: {S(12)}px; {font_style} }}")
        else:
            self.setText("?")
            self.setStyleSheet(f"QPushButton {{ background: {T('BG_KEY')}; color: {T('TEXT_MUTED')}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(12)}px; font-size: {S(28)}px; }} QPushButton:hover {{ border-color: #00D2FF; color: white; }}")


class MemoryMatchGame(QWidget):
    back_clicked = Signal()
    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self._audio = audio
        self._cards = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.header = _ViewHeader("Memory Match")
        self.header.back_clicked.connect(self.back_clicked)
        self.header.reset_clicked.connect(self._new_game)
        layout.addWidget(self.header)

        # 3-part Scoreboard
        score_layout = QHBoxLayout()
        score_layout.setContentsMargins(S(40), 0, S(40), 0)
        
        self._player_score_lbl = QLabel("👤 You: 0 Pairs")
        self._player_score_lbl.setStyleSheet(f"color: #00D2FF; font-size: {S(18)}px; font-weight: bold;")
        score_layout.addWidget(self._player_score_lbl)
        
        self._turn_badge = QLabel("🟢 YOUR TURN — Select 2 Cards")
        self._turn_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._turn_badge.setStyleSheet(f"background: {hex_to_rgba('#00F5D4', 0.15)}; border: 1px solid #00F5D4; color: #00F5D4; padding: {S(8)}px {S(20)}px; border-radius: {S(20)}px; font-weight: bold; font-size: {S(14)}px; letter-spacing: 1px;")
        score_layout.addWidget(self._turn_badge, 1, Qt.AlignmentFlag.AlignCenter)
        
        self._ai_score_lbl = QLabel("🤖 AI: 0 Pairs")
        self._ai_score_lbl.setStyleSheet(f"color: #FF6B6B; font-size: {S(18)}px; font-weight: bold;")
        score_layout.addWidget(self._ai_score_lbl)
        
        layout.addLayout(score_layout)

        # Grid
        self._grid_w = QWidget()
        self._grid = QGridLayout(self._grid_w)
        self._grid.setContentsMargins(S(80), S(20), S(80), S(40))
        layout.addWidget(self._grid_w, 1)
        
        # End Game Overlay
        self._end_modal = QFrame(self._grid_w)
        self._end_modal.setStyleSheet(f"QFrame {{ background: {hex_to_rgba('#0E1E2E', 0.95)}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(20)}px; }}")
        self._end_modal.hide()
        
        modal_layout = QVBoxLayout(self._end_modal)
        modal_layout.setContentsMargins(S(40), S(40), S(40), S(40))
        modal_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._end_title = QLabel("🏆 VICTORY!")
        self._end_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._end_title.setStyleSheet(f"color: #00D2FF; font-size: {S(48)}px; font-weight: 900; background: transparent; border: none;")
        modal_layout.addWidget(self._end_title)
        
        self._end_sub = QLabel("You outmatched the computer!")
        self._end_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._end_sub.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(24)}px; margin-bottom: {S(30)}px; background: transparent; border: none;")
        modal_layout.addWidget(self._end_sub)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(S(20))
        
        replay_btn = QPushButton("🔄 Play Again")
        replay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        replay_btn.setFixedSize(S(200), S(60))
        replay_btn.setStyleSheet(f"background: {T('ACCENT')}; color: white; border-radius: {S(12)}px; font-size: {S(20)}px; font-weight: bold;")
        replay_btn.clicked.connect(self._new_game)
        btn_layout.addWidget(replay_btn)
        
        back_btn = QPushButton("⬅️ Return to Games")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setFixedSize(S(240), S(60))
        back_btn.setStyleSheet(f"background: {T('BG_ELEVATED')}; color: {T('TEXT_PRIMARY')}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(12)}px; font-size: {S(20)}px; font-weight: bold;")
        back_btn.clicked.connect(self.back_clicked)
        btn_layout.addWidget(back_btn)
        
        modal_layout.addLayout(btn_layout)

        self._new_game()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Center modal
        if self._end_modal.isVisible():
            w = S(600)
            h = S(400)
            x = (self._grid_w.width() - w) // 2
            y = (self._grid_w.height() - h) // 2
            self._end_modal.setGeometry(x, y, w, h)

    def receive_blink(self):
        if self._locked or not self._is_player_turn: return
        for card in self._cards:
            if card.underMouse() and not card._flipped and not card._matched:
                card.activate.emit()
                break

    def hideEvent(self, event):
        super().hideEvent(event)
        try: self._new_game()
        except: pass

    def _new_game(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._cards.clear()
        self._end_modal.hide()
        
        self._first = self._second = None
        self._locked = False
        self._is_player_turn = True
        self._player_score = 0
        self._ai_score = 0
        self._ai_memory = {}
        
        self._update_score()
        self._set_turn_badge(True)

        symbols = ['🌟', '💎', '🔔', '🚀', '🍀', '🎈', '⚡', '👑', '🔥', '🎲'] * 2
        random.shuffle(symbols)

        for idx, sym in enumerate(symbols):
            c = _GazeFocusCard(sym)
            c.idx = idx
            c.activate.connect(lambda card=c: self._on_card(card))
            self._grid.addWidget(c, idx // 5, idx % 5)
            self._cards.append(c)
            
    def _set_turn_badge(self, is_player):
        self._is_player_turn = is_player
        if is_player:
            self._turn_badge.setText("🟢 YOUR TURN — Select 2 Cards")
            self._turn_badge.setStyleSheet(f"background: {hex_to_rgba('#00F5D4', 0.15)}; border: 1px solid #00F5D4; color: #00F5D4; padding: {S(8)}px {S(20)}px; border-radius: {S(20)}px; font-weight: bold; font-size: {S(14)}px; letter-spacing: 1px;")
        else:
            self._turn_badge.setText("🤖 COMPUTER IS THINKING...")
            self._turn_badge.setStyleSheet(f"background: {hex_to_rgba('#FFA502', 0.15)}; border: 1px solid #FFA502; color: #FFA502; padding: {S(8)}px {S(20)}px; border-radius: {S(20)}px; font-weight: bold; font-size: {S(14)}px; letter-spacing: 1px;")

    def _update_score(self):
        self._player_score_lbl.setText(f"👤 You: {self._player_score} Pairs")
        self._ai_score_lbl.setText(f"🤖 AI: {self._ai_score} Pairs")

    def _on_card(self, card, is_ai=False):
        if self._locked or card._flipped or card._matched: return
        if not is_ai and not self._is_player_turn: return
        
        if self._audio: self._audio.card_flip()
        card.flip_up()
        
        # Add to AI memory
        self._ai_memory[card.idx] = card._symbol
        
        if not self._first:
            self._first = card
        elif not self._second:
            self._second = card
            self._locked = True
            QTimer.singleShot(1200, lambda: self._evaluate(is_ai))

    def _evaluate(self, is_ai):
        is_match = (self._first._symbol == self._second._symbol)
        
        if is_match:
            self._first.mark_matched(is_ai)
            self._second.mark_matched(is_ai)
            if is_ai:
                self._ai_score += 1
            else:
                self._player_score += 1
            if self._audio: self._audio.card_match()
            self._update_score()
            
            # Remove matched cards from AI memory
            self._ai_memory.pop(self._first.idx, None)
            self._ai_memory.pop(self._second.idx, None)
        else:
            self._first.flip_down()
            self._second.flip_down()
            if self._audio: self._audio.card_mismatch()
            
        self._first = self._second = None
        self._locked = False
        
        if self._player_score + self._ai_score == 10:
            self._show_victory()
        elif is_match:
            # Match gets another turn
            if is_ai:
                QTimer.singleShot(1000, self._ai_turn_step1)
        else:
            # Mismatch switches turn
            self._set_turn_badge(is_ai)  # if is_ai was False (Player), next turn is AI (is_player=False)
            if not is_ai:
                QTimer.singleShot(800, self._ai_turn_step1)

    def _ai_turn_step1(self):
        if self._player_score + self._ai_score == 10 or self._is_player_turn: return
        self._locked = False
        
        # AI strategy
        known_pairs = {}
        for idx, sym in self._ai_memory.items():
            if not self._cards[idx]._matched:
                if sym in known_pairs:
                    known_pairs[sym].append(idx)
                else:
                    known_pairs[sym] = [idx]
                    
        # Find if AI knows a match (75% retention)
        match_idx = None
        if random.random() < 0.75:
            for sym, indices in known_pairs.items():
                if len(indices) >= 2:
                    match_idx = indices
                    break
                    
        if match_idx:
            self._ai_target_1 = match_idx[0]
            self._ai_target_2 = match_idx[1]
        else:
            unmatched = [i for i, c in enumerate(self._cards) if not c._matched and not c._flipped]
            if not unmatched: return
            self._ai_target_1 = random.choice(unmatched)
            self._ai_target_2 = None
            
        self._on_card(self._cards[self._ai_target_1], is_ai=True)
        QTimer.singleShot(900, self._ai_turn_step2)

    def _ai_turn_step2(self):
        if self._ai_target_2 is not None:
            # It remembered a pair
            target = self._ai_target_2
        else:
            # Let's see if the first card flipped matches anything in memory!
            sym1 = self._cards[self._ai_target_1]._symbol
            known_match = None
            if random.random() < 0.75:
                for idx, sym in self._ai_memory.items():
                    if sym == sym1 and idx != self._ai_target_1 and not self._cards[idx]._matched:
                        known_match = idx
                        break
            if known_match is not None:
                target = known_match
            else:
                unmatched = [i for i, c in enumerate(self._cards) if not c._matched and not c._flipped and i != self._ai_target_1]
                target = random.choice(unmatched)
                
        self._on_card(self._cards[target], is_ai=True)

    def _show_victory(self):
        self._locked = True
        w = S(600)
        h = S(400)
        x = (self._grid_w.width() - w) // 2
        y = (self._grid_w.height() - h) // 2
        self._end_modal.setGeometry(x, y, w, h)
        
        if self._player_score > self._ai_score:
            self._end_title.setText("🏆 VICTORY!")
            self._end_title.setStyleSheet(f"color: #00D2FF; font-size: {S(48)}px; font-weight: 900; background: transparent; border: none;")
            self._end_sub.setText(f"You outmatched the computer! Final Score: {self._player_score} - {self._ai_score}")
            if hasattr(self._audio, 'victory_fanfare'): self._audio.victory_fanfare()
        elif self._ai_score > self._player_score:
            self._end_title.setText("🤖 Computer Wins This Round!")
            self._end_title.setStyleSheet(f"color: #FF6B6B; font-size: {S(36)}px; font-weight: 900; background: transparent; border: none;")
            self._end_sub.setText(f"Great effort! Final Score: {self._player_score} - {self._ai_score}")
            if hasattr(self._audio, 'defeat_fanfare'): self._audio.defeat_fanfare()
        else:
            self._end_title.setText("🤝 It's a Tie! (5 - 5)")
            self._end_title.setStyleSheet(f"color: #F59E0B; font-size: {S(48)}px; font-weight: 900; background: transparent; border: none;")
            self._end_sub.setText("A perfectly matched battle!")
            if hasattr(self._audio, 'card_match'): self._audio.card_match()
            
        self._end_modal.show()
        self._end_modal.raise_()


class TicTacToeGame(QWidget):
    back_clicked = Signal()
    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self._audio = audio
        self._locked = False
        
        self._round = 1
        self._player_wins = 0
        self._ai_wins = 0
        self._ties = 0
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.header = _ViewHeader("Tic-Tac-Toe")
        self.header.back_clicked.connect(self.back_clicked)
        self.header.reset_clicked.connect(self._reset_tournament)
        layout.addWidget(self.header)
        
        # 3-part Scoreboard
        score_layout = QHBoxLayout()
        score_layout.setContentsMargins(S(40), 0, S(40), 0)
        
        self._round_lbl = QLabel("Round 1 of 3")
        self._round_lbl.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(18)}px; font-weight: bold;")
        score_layout.addWidget(self._round_lbl)
        
        self._turn_badge = QLabel("🟢 Your Turn (Blink to Place)")
        self._turn_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._turn_badge.setStyleSheet(f"background: {hex_to_rgba('#00F5D4', 0.15)}; border: 1px solid #00F5D4; color: #00F5D4; padding: {S(8)}px {S(20)}px; border-radius: {S(20)}px; font-weight: bold; font-size: {S(14)}px; letter-spacing: 1px;")
        score_layout.addWidget(self._turn_badge, 1, Qt.AlignmentFlag.AlignCenter)
        
        self._score_lbl = QLabel("👤 You: 0 | 🤖 AI: 0 | 🤝 Ties: 0")
        self._score_lbl.setStyleSheet(f"color: {T('ACCENT')}; font-size: {S(18)}px; font-weight: bold;")
        score_layout.addWidget(self._score_lbl)
        
        layout.addLayout(score_layout)

        self._grid_w = QWidget()
        self._grid_w.setFixedSize(S(400), S(400))
        self._grid = QGridLayout(self._grid_w)
        
        self._cells = []
        for i in range(9):
            btn = QPushButton("")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.setStyleSheet(f"QPushButton {{ background: {T('BG_CARD')}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(12)}px; font-size: {S(48)}px; }} QPushButton:hover {{ border-color: #00D2FF; }}")
            btn.clicked.connect(lambda checked=False, idx=i: self._on_cell(idx))
            self._grid.addWidget(btn, i // 3, i % 3)
            self._cells.append(btn)
            
        layout.addWidget(self._grid_w, 1, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(1)
        
        # End Game Overlay
        self._end_modal = QFrame(self._grid_w)
        self._end_modal.setStyleSheet(f"QFrame {{ background: {hex_to_rgba('#0E1E2E', 0.95)}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(20)}px; }}")
        self._end_modal.hide()
        
        modal_layout = QVBoxLayout(self._end_modal)
        modal_layout.setContentsMargins(S(40), S(40), S(40), S(40))
        modal_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._end_title = QLabel("")
        self._end_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        modal_layout.addWidget(self._end_title)
        
        self._end_sub = QLabel("")
        self._end_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        modal_layout.addWidget(self._end_sub)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(S(20))
        
        replay_btn = QPushButton("🔄 New Match")
        replay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        replay_btn.setFixedSize(S(200), S(60))
        replay_btn.setStyleSheet(f"background: {T('ACCENT')}; color: white; border-radius: {S(12)}px; font-size: {S(20)}px; font-weight: bold;")
        replay_btn.clicked.connect(self._reset_tournament)
        btn_layout.addWidget(replay_btn)
        
        back_btn = QPushButton("⬅️ Back to Games")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setFixedSize(S(240), S(60))
        back_btn.setStyleSheet(f"background: {T('BG_ELEVATED')}; color: {T('TEXT_PRIMARY')}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(12)}px; font-size: {S(20)}px; font-weight: bold;")
        back_btn.clicked.connect(self.back_clicked)
        btn_layout.addWidget(back_btn)
        
        modal_layout.addLayout(btn_layout)

        self._start_round()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._end_modal.isVisible():
            w = S(500)
            h = S(350)
            x = (self._grid_w.width() - w) // 2
            y = (self._grid_w.height() - h) // 2
            self._end_modal.setGeometry(x, y, w, h)

    def receive_blink(self):
        if self._locked: return
        for i, btn in enumerate(self._cells):
            if btn.underMouse() and self._board[i] == 0:
                btn.click()
                break

    def hideEvent(self, event):
        super().hideEvent(event)
        try: self._reset_tournament()
        except: pass

    def _reset_tournament(self):
        self._round = 1
        self._player_wins = 0
        self._ai_wins = 0
        self._ties = 0
        self._end_modal.hide()
        self._start_round()

    def _start_round(self):
        self._board = [0]*9
        self._locked = False
        
        self._round_lbl.setText(f"Round {self._round} of 3")
        self._score_lbl.setText(f"👤 You: {self._player_wins} | 🤖 AI: {self._ai_wins} | 🤝 Ties: {self._ties}")
        self._turn_badge.setText("🟢 Your Turn (Blink to Place)")
        self._turn_badge.setStyleSheet(f"background: {hex_to_rgba('#00F5D4', 0.15)}; border: 1px solid #00F5D4; color: #00F5D4; padding: {S(8)}px {S(20)}px; border-radius: {S(20)}px; font-weight: bold; font-size: {S(14)}px; letter-spacing: 1px;")

        for btn in self._cells:
            btn.setText("")
            btn.setStyleSheet(f"QPushButton {{ background: {T('BG_CARD')}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(12)}px; font-size: {S(48)}px; }} QPushButton:hover {{ border-color: #00D2FF; }}")

    def _on_cell(self, idx):
        if self._locked or self._board[idx] != 0: return
        if self._audio: self._audio.ui_click()
        
        self._board[idx] = 1
        self._cells[idx].setText("X")
        self._cells[idx].setStyleSheet(f"QPushButton {{ color: #00D2FF; background: {hex_to_rgba('#00D2FF', 0.1)}; border: 2px solid #00D2FF; border-radius: {S(12)}px; font-size: {S(48)}px; }}")
        
        if self._check_win(1):
            self._end_round("win")
            return
        if 0 not in self._board:
            self._end_round("tie")
            return
            
        self._locked = True
        self._turn_badge.setText("🤖 AI is Thinking...")
        self._turn_badge.setStyleSheet(f"background: {hex_to_rgba('#FFA502', 0.15)}; border: 1px solid #FFA502; color: #FFA502; padding: {S(8)}px {S(20)}px; border-radius: {S(20)}px; font-weight: bold; font-size: {S(14)}px; letter-spacing: 1px;")
        QTimer.singleShot(600, self._ai_move)

    def _ai_move(self):
        best_score = -float('inf')
        best_move = -1
        for i in range(9):
            if self._board[i] == 0:
                self._board[i] = -1
                score = self._minimax(self._board, 0, False)
                self._board[i] = 0
                if score > best_score:
                    best_score = score
                    best_move = i
                    
        self._board[best_move] = -1
        self._cells[best_move].setText("O")
        self._cells[best_move].setStyleSheet(f"QPushButton {{ color: #FF7F50; background: {hex_to_rgba('#FF7F50', 0.1)}; border: 2px solid #FF7F50; border-radius: {S(12)}px; font-size: {S(48)}px; }}")
        
        if self._audio: self._audio.ui_click()
        
        if self._check_win(-1):
            self._end_round("lose")
        elif 0 not in self._board:
            self._end_round("tie")
        else:
            self._turn_badge.setText("🟢 Your Turn (Blink to Place)")
            self._turn_badge.setStyleSheet(f"background: {hex_to_rgba('#00F5D4', 0.15)}; border: 1px solid #00F5D4; color: #00F5D4; padding: {S(8)}px {S(20)}px; border-radius: {S(20)}px; font-weight: bold; font-size: {S(14)}px; letter-spacing: 1px;")
            self._locked = False

    def _minimax(self, board, depth, is_max):
        if self._check_win(-1): return 10 - depth
        if self._check_win(1): return -10 + depth
        if 0 not in board: return 0
        
        if is_max:
            best = -float('inf')
            for i in range(9):
                if board[i] == 0:
                    board[i] = -1
                    best = max(best, self._minimax(board, depth + 1, not is_max))
                    board[i] = 0
            return best
        else:
            best = float('inf')
            for i in range(9):
                if board[i] == 0:
                    board[i] = 1
                    best = min(best, self._minimax(board, depth + 1, not is_max))
                    board[i] = 0
            return best

    def _check_win(self, p):
        b = self._board
        wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
        return any(b[i]==p and b[j]==p and b[k]==p for i,j,k in wins)

    def _end_round(self, result):
        self._locked = True
        
        if result == "win":
            self._player_wins += 1
            if self._audio: self._audio.card_match()
            self._turn_badge.setText("Round Complete! You Win")
        elif result == "lose":
            self._ai_wins += 1
            if self._audio: self._audio.card_mismatch()
            self._turn_badge.setText("Round Complete! AI Wins")
        else:
            self._ties += 1
            if self._audio: self._audio.ui_click()
            self._turn_badge.setText("Round Complete! Draw")
            
        self._score_lbl.setText(f"👤 You: {self._player_wins} | 🤖 AI: {self._ai_wins} | 🤝 Ties: {self._ties}")
        self._turn_badge.setStyleSheet(f"background: {hex_to_rgba('#F59E0B', 0.15)}; border: 1px solid #F59E0B; color: #F59E0B; padding: {S(8)}px {S(20)}px; border-radius: {S(20)}px; font-weight: bold; font-size: {S(14)}px; letter-spacing: 1px;")

        if self._round < 3:
            self._round += 1
            QTimer.singleShot(1500, self._start_round)
        else:
            QTimer.singleShot(1500, self._show_tournament_result)

    def _show_tournament_result(self):
        w = S(500)
        h = S(350)
        x = (self._grid_w.width() - w) // 2
        y = (self._grid_w.height() - h) // 2
        self._end_modal.setGeometry(x, y, w, h)
        
        if self._player_wins > self._ai_wins:
            self._end_title.setText("🏆 TOURNAMENT CHAMPION!")
            self._end_title.setStyleSheet(f"color: #00D2FF; font-size: {S(36)}px; font-weight: 900; background: transparent; border: none;")
            self._end_sub.setText(f"Final Score: You {self._player_wins} - {self._ai_wins} Computer")
            self._end_sub.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(20)}px; margin-bottom: {S(30)}px; background: transparent; border: none;")
            if hasattr(self._audio, 'victory_fanfare'): self._audio.victory_fanfare()
        elif self._ai_wins > self._player_wins:
            self._end_title.setText("🤖 Computer Won the Match!")
            self._end_title.setStyleSheet(f"color: #FF6B6B; font-size: {S(28)}px; font-weight: 900; background: transparent; border: none;")
            self._end_sub.setText(f"Final Score: Computer {self._ai_wins} - {self._player_wins} You")
            self._end_sub.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(20)}px; margin-bottom: {S(30)}px; background: transparent; border: none;")
            if hasattr(self._audio, 'defeat_fanfare'): self._audio.defeat_fanfare()
        else:
            self._end_title.setText("🤝 Tournament Draw!")
            self._end_title.setStyleSheet(f"color: #F59E0B; font-size: {S(36)}px; font-weight: 900; background: transparent; border: none;")
            self._end_sub.setText(f"Final Score: You {self._player_wins} - {self._ai_wins} Computer")
            self._end_sub.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(20)}px; margin-bottom: {S(30)}px; background: transparent; border: none;")
            if hasattr(self._audio, 'card_match'): self._audio.card_match()
            
        self._end_modal.show()
        self._end_modal.raise_()


class BubbleArenaWidget(QWidget):
    bubble_popped = Signal(int, float, float)
    bubble_escaped = Signal()
    bomb_hit = Signal()

    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self._audio = audio
        self.setMouseTracking(True)
        self._bubbles = []
        self._particles = []
        self._time = 0.0
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_physics)
        
        self._spawn_timer = QTimer(self)
        self._spawn_timer.timeout.connect(self._spawn_bubble)

    def start(self):
        self._bubbles.clear()
        self._particles.clear()
        self._time = 0.0
        self._timer.start(16)
        self._spawn_timer.start(1200)

    def stop(self):
        self._timer.stop()
        self._spawn_timer.stop()
        self._bubbles.clear()
        self.update()

    def _spawn_bubble(self):
        w = self.width()
        if w < 100: return
        
        size = random.randint(S(60), S(110))
        # Avoid PiP bottom right
        x = random.randint(S(20), max(S(20), w - size - S(20)))
        y = self.height() + size
        
        if x > w - S(300) and y > self.height() - S(250):
            x = x - S(300)
        
        r = random.random()
        if r < 0.15: btype = 'bomb'
        elif r < 0.25: btype = 'gold'
        else: btype = 'standard'
            
        speed = random.uniform(S(60), S(120))
        wobble_speed = random.uniform(2.0, 4.0)
        seed = random.uniform(0, 100)
        
        self._bubbles.append({
            'x': x,
            'y': y,
            'base_x': x,
            'size': size,
            'type': btype,
            'speed': speed,
            'wobble_speed': wobble_speed,
            'seed': seed,
            'popping': 0.0
        })

    def _update_physics(self):
        dt = 0.016
        self._time += dt
        
        import math
        new_bubbles = []
        for b in self._bubbles:
            if b['popping'] > 0:
                b['popping'] += dt * 5.0
                if b['popping'] < 1.0:
                    new_bubbles.append(b)
                continue
                
            b['y'] -= b['speed'] * dt
            b['x'] = b['base_x'] + math.sin(self._time * b['wobble_speed'] + b['seed']) * S(30)
            
            if b['y'] + b['size'] < 0:
                if b['type'] != 'bomb':
                    self.bubble_escaped.emit()
            else:
                new_bubbles.append(b)
                
        self._bubbles = new_bubbles
        
        new_particles = []
        for p in self._particles:
            p['life'] -= dt
            if p['life'] > 0:
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['vy'] += S(400) * dt
                new_particles.append(p)
        self._particles = new_particles
        
        self.update()

    def receive_blink(self, cursor_pos):
        cx = cursor_pos.x()
        cy = cursor_pos.y()
        
        import math
        for b in reversed(self._bubbles):
            if b['popping'] > 0: continue
            
            bx = b['x'] + b['size']/2
            by = b['y'] + b['size']/2
            r = b['size']/2
            
            dist = math.sqrt((cx - bx)**2 + (cy - by)**2)
            if dist <= r:
                b['popping'] = 0.01
                if b['type'] == 'bomb':
                    self.bomb_hit.emit()
                else:
                    pts = 100 if b['type'] == 'gold' else 30
                    self.bubble_popped.emit(pts, bx, by)
                    
                for i in range(8):
                    angle = i * (2 * math.pi / 8)
                    speed = random.uniform(S(100), S(250))
                    self._particles.append({
                        'x': bx,
                        'y': by,
                        'vx': math.cos(angle) * speed,
                        'vy': math.sin(angle) * speed,
                        'life': 0.5,
                        'max_life': 0.5,
                        'type': b['type']
                    })
                break

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.receive_blink(event.pos())
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for b in self._bubbles:
            r = b['size'] / 2
            cx = b['x'] + r
            cy = b['y'] + r
            
            if b['popping'] > 0:
                alpha = int(255 * (1.0 - b['popping']))
                pr = r + S(20) * b['popping']
                painter.setPen(QPen(QColor(255, 255, 255, alpha), 3))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(cx, cy), pr, pr)
                continue
                
            if b['type'] == 'bomb':
                base_color = QColor(255, 71, 87, 180)
                border_color = QColor(255, 71, 87, 255)
            elif b['type'] == 'gold':
                base_color = QColor(252, 211, 77, 100)
                border_color = QColor(252, 211, 77, 200)
            else:
                base_color = QColor(0, 210, 255, 40)
                border_color = QColor(255, 255, 255, 120)
                
            grad = QRadialGradient(cx - r*0.3, cy - r*0.3, r)
            grad.setColorAt(0, QColor(255, 255, 255, 180))
            grad.setColorAt(0.3, base_color)
            grad.setColorAt(1, border_color)
            
            painter.setPen(QPen(border_color, 2))
            painter.setBrush(QBrush(grad))
            painter.drawEllipse(QPointF(cx, cy), r, r)
            
            if b['type'] == 'bomb':
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0,0,0,100))
                painter.drawEllipse(QPointF(cx, cy), r*0.4, r*0.4)
                painter.setPen(QColor(255,255,255))
                painter.setFont(QFont("Arial", int(r*0.4), QFont.Weight.Bold))
                painter.drawText(QRectF(cx-r, cy-r, r*2, r*2), Qt.AlignmentFlag.AlignCenter, "💣")
                
        for p in self._particles:
            alpha = int(255 * (p['life'] / p['max_life']))
            if p['type'] == 'bomb': c = QColor(255, 71, 87, alpha)
            elif p['type'] == 'gold': c = QColor(252, 211, 77, alpha)
            else: c = QColor(0, 210, 255, alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(c)
            painter.drawEllipse(QPointF(p['x'], p['y']), S(4), S(4))
            painter.end()


class ZenBubblePopGame(QWidget):
    back_clicked = Signal()
    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self._audio = audio
        self._running = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.header = _ViewHeader("Zen Bubble Pop")
        self.header.back_clicked.connect(self.back_clicked)
        self.header.reset_clicked.connect(self._reset_game)
        layout.addWidget(self.header)
        
        score_layout = QHBoxLayout()
        score_layout.setContentsMargins(S(40), 0, S(40), 0)
        
        self._score_lbl = QLabel("Score: 0")
        self._score_lbl.setStyleSheet(f"color: #00D2FF; font-size: {S(18)}px; font-weight: bold;")
        score_layout.addWidget(self._score_lbl)
        
        self._miss_lbl = QLabel("Missed: 0 / 5  🫧 🫧 🫧 🫧 🫧")
        self._miss_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._miss_lbl.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(18)}px; font-weight: bold;")
        score_layout.addWidget(self._miss_lbl, 1)
        
        layout.addLayout(score_layout)
        
        self._arena = BubbleArenaWidget(self._audio)
        self._arena.bubble_popped.connect(self._on_bubble_popped)
        self._arena.bubble_escaped.connect(self._on_bubble_escaped)
        self._arena.bomb_hit.connect(self._on_bomb_hit)
        layout.addWidget(self._arena, 1)
        
        # End Game Overlay
        self._end_modal = QFrame(self._arena)
        self._end_modal.setStyleSheet(f"QFrame {{ background: {hex_to_rgba('#0E1E2E', 0.95)}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(20)}px; }}")
        self._end_modal.hide()
        
        modal_layout = QVBoxLayout(self._end_modal)
        modal_layout.setContentsMargins(S(40), S(40), S(40), S(40))
        modal_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._end_title = QLabel("")
        self._end_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        modal_layout.addWidget(self._end_title)
        
        self._end_stats = QLabel("")
        self._end_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._end_stats.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(18)}px; margin-bottom: {S(20)}px; background: transparent; border: none;")
        modal_layout.addWidget(self._end_stats)
        
        self._end_score = QLabel("")
        self._end_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._end_score.setStyleSheet(f"color: #00D2FF; font-size: {S(64)}px; font-weight: 900; background: transparent; border: none; margin-bottom: {S(20)}px;")
        modal_layout.addWidget(self._end_score)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(S(20))
        
        replay_btn = QPushButton("🔄 Pop Again")
        replay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        replay_btn.setFixedSize(S(200), S(60))
        replay_btn.setStyleSheet(f"background: {T('ACCENT')}; color: white; border-radius: {S(12)}px; font-size: {S(20)}px; font-weight: bold;")
        replay_btn.clicked.connect(self._reset_game)
        btn_layout.addWidget(replay_btn)
        
        back_btn = QPushButton("⬅️ Back to Games")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setFixedSize(S(240), S(60))
        back_btn.setStyleSheet(f"background: {T('BG_ELEVATED')}; color: {T('TEXT_PRIMARY')}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(12)}px; font-size: {S(20)}px; font-weight: bold;")
        back_btn.clicked.connect(self.back_clicked)
        btn_layout.addWidget(back_btn)
        
        modal_layout.addLayout(btn_layout)
        
        self._floating_lbls = []
        
        self._score = 0
        self._missed = 0
        self._popped = 0
        self._golden = 0
        
        self._roll_timer = QTimer(self)
        self._roll_timer.timeout.connect(self._roll_score)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._end_modal.isVisible():
            w = S(600)
            h = S(450)
            x = (self._arena.width() - w) // 2
            y = (self._arena.height() - h) // 2
            self._end_modal.setGeometry(x, y, w, h)

    def showEvent(self, event):
        self._reset_game()

    def hideEvent(self, event):
        self._running = False
        self._arena.stop()

    def _reset_game(self):
        self._score = 0
        self._missed = 0
        self._popped = 0
        self._golden = 0
        self._running = True
        self._end_modal.hide()
        self._update_ui()
        self._arena.start()

    def _update_ui(self):
        self._score_lbl.setText(f"Score: {self._score}")
        bubbles = "🫧 " * (5 - self._missed) + "✖ " * self._missed
        self._miss_lbl.setText(f"Missed: {self._missed} / 5  {bubbles.strip()}")

    def receive_blink(self):
        if not self._running: return
        cursor_pos = self._arena.mapFromGlobal(self._arena.cursor().pos())
        self._arena.receive_blink(cursor_pos)

    def _on_bubble_popped(self, pts, x, y):
        self._score += pts
        self._popped += 1
        if pts == 100:
            self._golden += 1
            if self._audio: self._audio.chime_note(880)
            self._spawn_floating_text(f"+100", "#FCD34D", x, y)
        else:
            if self._audio: self._audio.bubble_water_pop()
            self._spawn_floating_text(f"+30", "#00D2FF", x, y)
        self._update_ui()

    def _on_bubble_escaped(self):
        if not self._running: return
        self._missed += 1
        self._update_ui()
        if self._audio: self._audio.miss()
        if self._missed >= 5:
            self._end_game("ZEN RETREAT ENDED", "#00D2FF")

    def _on_bomb_hit(self):
        if not self._running: return
        if self._audio: self._audio.bomb_blast()
        
        # Screen shake
        anim = QPropertyAnimation(self, b"pos")
        anim.setDuration(400)
        p = self.pos()
        anim.setKeyValueAt(0, p)
        anim.setKeyValueAt(0.2, p + QPoint(S(10), -S(10)))
        anim.setKeyValueAt(0.4, p + QPoint(-S(10), S(10)))
        anim.setKeyValueAt(0.6, p + QPoint(S(10), S(10)))
        anim.setKeyValueAt(0.8, p + QPoint(-S(10), -S(10)))
        anim.setKeyValueAt(1, p)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        
        QTimer.singleShot(400, lambda: self._end_game("💥 DETONATED!", "#FF4757"))

    def _spawn_floating_text(self, text, color, x, y):
        lbl = QLabel(text, self._arena)
        lbl.setStyleSheet(f"color: {color}; font-size: {S(24)}px; font-weight: bold; background: transparent;")
        lbl.move(x, y)
        lbl.show()
        
        anim1 = QPropertyAnimation(lbl, b"pos")
        anim1.setDuration(1000)
        anim1.setStartValue(lbl.pos())
        anim1.setEndValue(lbl.pos() - QPoint(0, S(80)))
        anim1.setEasingCurve(QEasingCurve.Type.OutQuad)
        anim1.finished.connect(lbl.deleteLater)
        anim1.start()
        self._floating_lbls.append((lbl, anim1))

    def _end_game(self, title, color):
        self._running = False
        self._arena.stop()
        
        w = S(600)
        h = S(450)
        x = (self._arena.width() - w) // 2
        y = (self._arena.height() - h) // 2
        self._end_modal.setGeometry(x, y, w, h)
        
        self._end_title.setText(title)
        self._end_title.setStyleSheet(f"color: {color}; font-size: {S(36)}px; font-weight: 900; background: transparent; border: none;")
        self._end_stats.setText(f"Bubbles Cleared: {self._popped} | Golden Bubbles: {self._golden} | Escaped: {self._missed} / 5")
        
        self._displayed_score = 0
        self._end_score.setText("0")
        
        self._end_modal.show()
        self._end_modal.raise_()
        self._roll_timer.start(30)

    def _roll_score(self):
        if self._displayed_score < self._score:
            self._displayed_score += max(1, self._score // 30)
            if self._displayed_score > self._score:
                self._displayed_score = self._score
            self._end_score.setText(str(self._displayed_score))
        else:
            self._roll_timer.stop()


class SimonRingWidget(QWidget):
    pad_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(S(400), S(400))
        self.setMouseTracking(True)
        
        self.arcs = [
            (45 * 16, 90 * 16, QColor("#00F5D4"), 261.6), # Top
            (315 * 16, 90 * 16, QColor("#00D2FF"), 329.6), # Right
            (225 * 16, 90 * 16, QColor("#FFA502"), 392.0), # Bottom
            (135 * 16, 90 * 16, QColor("#FF4757"), 523.3)  # Left
        ]
        
        self.active_pad = -1
        self.hover_pad = -1
        self.center_text = "ROUND 1"
        self.center_subtext = ""
        self.shockwave_radius = 0
        self.shockwave_color = QColor(255,255,255)
        
        self.anim = QPropertyAnimation(self, b"shockwave_radius")
        self.anim.setDuration(400)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.dwell_timer = QTimer(self)
        self.dwell_timer.setSingleShot(True)
        self.dwell_timer.setInterval(800)
        self.dwell_timer.timeout.connect(self._on_dwell_timeout)
        
        self.dwell_anim = QVariantAnimation(self)
        self.dwell_anim.setDuration(800)
        self.dwell_anim.setStartValue(0.0)
        self.dwell_anim.setEndValue(100.0)
        self.dwell_anim.valueChanged.connect(self._on_dwell_anim)
        self.dwell_progress = 0.0
        
    def _on_dwell_timeout(self):
        if self.hover_pad != -1:
            self.pad_clicked.emit(self.hover_pad)

    def _on_dwell_anim(self, val):
        self.dwell_progress = val
        self.update()
        
    def get_pad_at(self, pos):
        import math
        cx = self.width() / 2
        cy = self.height() / 2
        dx = pos.x() - cx
        dy = pos.y() - cy
        
        dist = math.hypot(dx, dy)
        if dist < S(60) or dist > S(180):
            return -1
            
        angle = math.degrees(math.atan2(-dy, dx))
        if angle < 0: angle += 360
        
        if 45 <= angle < 135: return 0
        elif 135 <= angle < 225: return 3
        elif 225 <= angle < 315: return 2
        else: return 1

    def receive_blink(self, pos=None):
        if pos is not None:
            pad = self.get_pad_at(pos)
        else:
            pad = self.hover_pad
            
        if pad != -1:
            self.pad_clicked.emit(pad)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.receive_blink(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pad = self.get_pad_at(event.pos())
        if pad != self.hover_pad:
            self.hover_pad = pad
            if pad != -1:
                self.dwell_timer.start()
                self.dwell_anim.start()
            else:
                self.dwell_timer.stop()
                self.dwell_anim.stop()
            self.dwell_progress = 0.0
            self.update()
            
    def leaveEvent(self, event):
        self.hover_pad = -1
        self.dwell_timer.stop()
        self.dwell_anim.stop()
        self.dwell_progress = 0.0
        self.update()
        super().leaveEvent(event)

    def flash(self, pad):
        self.active_pad = pad
        self.shockwave_radius = S(60)
        self.shockwave_color = self.arcs[pad][2]
        self.anim.setStartValue(S(60))
        self.anim.setEndValue(S(250))
        self.anim.start()
        self.update()
        QTimer.singleShot(350, self.unflash)
        
    def unflash(self):
        self.active_pad = -1
        self.update()

    def set_text(self, main, sub=""):
        self.center_text = main
        self.center_subtext = sub
        self.update()

    def set_shockwave_radius(self, r):
        self._sw = r
        self.update()
        
    def get_shockwave_radius(self):
        return getattr(self, '_sw', 0)
        
    shockwave_radius = Property(float, get_shockwave_radius, set_shockwave_radius)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx = self.width() / 2
        cy = self.height() / 2
        
        if getattr(self, '_sw', 0) > S(60):
            r = self._sw
            alpha = int(255 * (1.0 - (r - S(60)) / S(190)))
            c = QColor(self.shockwave_color)
            c.setAlpha(max(0, alpha))
            painter.setPen(QPen(c, 4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), r, r)
            
        r_outer = S(180)
        r_inner = S(60)
        
        for i, (start, span, color, _) in enumerate(self.arcs):
            is_active = (i == self.active_pad)
            is_hover = (i == self.hover_pad)
            
            c = QColor(color)
            if is_active: c.setAlpha(255)
            elif is_hover: c.setAlpha(180)
            else: c.setAlpha(80)
                
            path = QPainterPath()
            path.arcMoveTo(QRectF(cx - r_outer, cy - r_outer, r_outer*2, r_outer*2), start/16.0)
            path.arcTo(QRectF(cx - r_outer, cy - r_outer, r_outer*2, r_outer*2), start/16.0, span/16.0)
            path.arcTo(QRectF(cx - r_inner, cy - r_inner, r_inner*2, r_inner*2), (start+span)/16.0, -span/16.0)
            path.closeSubpath()
            
            if is_active:
                painter.setPen(QPen(color, 2))
            else:
                painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(c)
            painter.drawPath(path)
            
            if is_active:
                c_bloom = QColor(color)
                c_bloom.setAlpha(50)
                painter.setPen(QPen(c_bloom, 10))
                painter.drawPath(path)
                c_bloom.setAlpha(20)
                painter.setPen(QPen(c_bloom, 20))
                painter.drawPath(path)
                
            if is_hover and self.dwell_progress > 0:
                c_dwell = QColor(255, 255, 255, 80)
                path_dwell = QPainterPath()
                span_dwell = (span / 16.0) * (self.dwell_progress / 100.0)
                path_dwell.arcMoveTo(QRectF(cx - r_outer, cy - r_outer, r_outer*2, r_outer*2), start/16.0)
                path_dwell.arcTo(QRectF(cx - r_outer, cy - r_outer, r_outer*2, r_outer*2), start/16.0, span_dwell)
                path_dwell.arcTo(QRectF(cx - r_inner, cy - r_inner, r_inner*2, r_inner*2), (start/16.0)+span_dwell, -span_dwell)
                path_dwell.closeSubpath()
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(c_dwell)
                painter.drawPath(path_dwell)
                
        painter.setPen(QPen(QColor(255,255,255,100), 2))
        painter.setBrush(QColor(14, 30, 46, 255))
        painter.drawEllipse(QPointF(cx, cy), r_inner, r_inner)
        
        painter.setPen(QColor(255,255,255))
        painter.setFont(QFont("Arial", S(14), QFont.Weight.Bold))
        painter.drawText(QRectF(cx-r_inner, cy-S(15), r_inner*2, S(30)), Qt.AlignmentFlag.AlignCenter, self.center_text)
        
        if self.center_subtext:
            painter.setPen(QColor(150,150,150))
            painter.setFont(QFont("Arial", S(10)))
            painter.drawText(QRectF(cx-r_inner, cy+S(10), r_inner*2, S(20)), Qt.AlignmentFlag.AlignCenter, self.center_subtext)
            painter.end()


class SimonSequenceGame(QWidget):
    back_clicked = Signal()
    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self._audio = audio
        self._sequence = []
        self._player_idx = 0
        self._locked = True
        self._score = 0
        self._streak = 0
        self._max_streak = 0
        self._round_start_time = 0.0
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.header = _ViewHeader("Simon Sequence")
        self.header.back_clicked.connect(self.back_clicked)
        self.header.reset_clicked.connect(self._reset_game)
        layout.addWidget(self.header)
        
        score_layout = QHBoxLayout()
        score_layout.setContentsMargins(S(40), 0, S(40), 0)
        
        self._score_lbl = QLabel("Score: 0")
        self._score_lbl.setStyleSheet(f"color: #00D2FF; font-size: {S(18)}px; font-weight: bold;")
        score_layout.addWidget(self._score_lbl)
        
        self._streak_lbl = QLabel("Streak: 0 | Max: 0")
        self._streak_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._streak_lbl.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(18)}px; font-weight: bold;")
        score_layout.addWidget(self._streak_lbl, 1)
        
        layout.addLayout(score_layout)
        
        self._arena = QWidget()
        arena_layout = QVBoxLayout(self._arena)
        
        self._start_btn = DwellButton("▶ Start Sequence", dwell_ms=800)
        self._start_btn.setFixedSize(S(200), S(50))
        self._start_btn.clicked.connect(self._next_round)
        arena_layout.addWidget(self._start_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        self._ring = SimonRingWidget()
        self._ring.pad_clicked.connect(self._on_pad)
        arena_layout.addWidget(self._ring, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self._arena, 1)
        
        # End Modal
        self._end_modal = QFrame(self._arena)
        self._end_modal.setStyleSheet(f"QFrame {{ background: {hex_to_rgba('#0E1E2E', 0.95)}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(20)}px; }}")
        self._end_modal.hide()
        
        modal_layout = QVBoxLayout(self._end_modal)
        modal_layout.setContentsMargins(S(40), S(40), S(40), S(40))
        modal_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._end_title = QLabel("SEQUENCE BROKEN")
        self._end_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._end_title.setStyleSheet(f"color: #FF4757; font-size: {S(36)}px; font-weight: 900; background: transparent; border: none;")
        modal_layout.addWidget(self._end_title)
        
        self._end_stats = QLabel("")
        self._end_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._end_stats.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(18)}px; margin-bottom: {S(20)}px; background: transparent; border: none;")
        modal_layout.addWidget(self._end_stats)
        
        self._end_score = QLabel("")
        self._end_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._end_score.setStyleSheet(f"color: #00D2FF; font-size: {S(64)}px; font-weight: 900; background: transparent; border: none; margin-bottom: {S(10)}px;")
        modal_layout.addWidget(self._end_score)
        
        self._end_badge = QLabel("")
        self._end_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._end_badge.setStyleSheet(f"color: #F59E0B; font-size: {S(24)}px; font-weight: bold; background: transparent; border: none; margin-bottom: {S(20)}px;")
        modal_layout.addWidget(self._end_badge)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(S(20))
        
        replay_btn = QPushButton("🔄 Retry Sequence")
        replay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        replay_btn.setFixedSize(S(240), S(60))
        replay_btn.setStyleSheet(f"background: {T('ACCENT')}; color: white; border-radius: {S(12)}px; font-size: {S(20)}px; font-weight: bold;")
        replay_btn.clicked.connect(self._reset_game)
        btn_layout.addWidget(replay_btn)
        
        back_btn = QPushButton("⬅️ Back to Games")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setFixedSize(S(240), S(60))
        back_btn.setStyleSheet(f"background: {T('BG_ELEVATED')}; color: {T('TEXT_PRIMARY')}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(12)}px; font-size: {S(20)}px; font-weight: bold;")
        back_btn.clicked.connect(self.back_clicked)
        btn_layout.addWidget(back_btn)
        
        modal_layout.addLayout(btn_layout)
        
        self._roll_timer = QTimer(self)
        self._roll_timer.timeout.connect(self._roll_score)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._end_modal.isVisible():
            w = S(600)
            h = S(450)
            x = (self._arena.width() - w) // 2
            y = (self._arena.height() - h) // 2
            self._end_modal.setGeometry(x, y, w, h)

    def receive_blink(self):
        if not self._locked and not self._end_modal.isVisible():
            self._ring.receive_blink()

    def hideEvent(self, event):
        super().hideEvent(event)
        try: self._reset_game()
        except: pass

    def _reset_game(self):
        self._sequence.clear()
        self._locked = True
        self._score = 0
        self._streak = 0
        self._end_modal.hide()
        self._start_btn.show()
        self._ring.set_text("READY")
        self._update_ui()

    def _update_ui(self):
        self._score_lbl.setText(f"Score: {self._score}")
        self._streak_lbl.setText(f"Streak: {self._streak} | Max: {self._max_streak}")

    def _next_round(self):
        self._locked = True
        self._start_btn.hide()
        self._player_idx = 0
        self._sequence.append(random.randint(0, 3))
        self._ring.set_text(f"ROUND {len(self._sequence)}", "Watch Pattern")
        QTimer.singleShot(1000, self._play_sequence)

    def _play_sequence(self):
        def play_step(idx):
            import time
            if idx >= len(self._sequence):
                self._locked = False
                self._ring.set_text(f"ROUND {len(self._sequence)}", "Blink to Select")
                self._round_start_time = time.time()
                return
            pad_idx = self._sequence[idx]
            self._ring.flash(pad_idx)
            if self._audio: self._audio.play_tone(self._ring.arcs[pad_idx][3], 'sine', 0.35, 0.12, decay='exponential')
            QTimer.singleShot(550, lambda: play_step(idx + 1))
        play_step(0)

    def _on_pad(self, idx):
        import time
        if self._locked: return
        
        now = time.time()
        if now - getattr(self, '_last_pad_time', 0) < 0.25:
            return
        self._last_pad_time = now
        
        self._ring.flash(idx)
        
        if self._sequence[self._player_idx] == idx:
            if self._audio: self._audio.play_tone(self._ring.arcs[idx][3], 'sine', 0.35, 0.12, decay='exponential')
            self._player_idx += 1
            if self._player_idx == len(self._sequence):
                self._locked = True
                self._ring.set_text("CORRECT!")
                
                dt = time.time() - self._round_start_time
                mult = 1.5 if dt <= 3.0 else 1.0
                pts = int(len(self._sequence) * 100 * mult)
                self._score += pts
                self._streak += 1
                if self._streak > self._max_streak:
                    self._max_streak = self._streak
                self._update_ui()
                
                QTimer.singleShot(1000, self._next_round)
        else:
            self._locked = True
            if self._audio: self._audio.miss()
            self._ring.set_text("BROKEN")
            QTimer.singleShot(500, self._show_end)

    def _show_end(self):
        self._end_stats.setText(f"Max Sequence Length: {len(self._sequence) - 1} Notes")
        self._displayed_score = 0
        self._end_score.setText("0")
        self._end_badge.setText("")
        
        w = S(600)
        h = S(450)
        x = (self._arena.width() - w) // 2
        y = (self._arena.height() - h) // 2
        self._end_modal.setGeometry(x, y, w, h)
        
        self._end_modal.show()
        self._end_modal.raise_()
        self._roll_timer.start(30)

    def _roll_score(self):
        if self._displayed_score < self._score:
            self._displayed_score += max(1, self._score // 30)
            if self._displayed_score > self._score:
                self._displayed_score = self._score
            self._end_score.setText(str(self._displayed_score))
        else:
            self._roll_timer.stop()
            lvl = len(self._sequence) - 1
            if lvl >= 8: badge = "🧠 Master of Sequence"
            elif lvl >= 4: badge = "⚡ Agile Focus"
            else: badge = "🌱 Apprentice Mind"
            self._end_badge.setText(badge)


class PrecisionTargetWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(S(140), S(140))
        self._scale = 1.0
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(2500)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.7)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.anim.setLoopCount(-1)
        self.anim.valueChanged.connect(self._update_scale)
        
    def showEvent(self, e):
        self.anim.start()
        super().showEvent(e)
        
    def hideEvent(self, e):
        self.anim.stop()
        super().hideEvent(e)

    def _update_scale(self, val):
        self._scale = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        
        # Base sizes
        r_outer = S(60) * self._scale
        r_inner = S(35) * self._scale
        r_core = S(15) * self._scale
        
        # Outer Ring
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 210, 255, 50))
        painter.drawEllipse(QPointF(cx, cy), r_outer, r_outer)
        
        # Inner Ring
        painter.setBrush(QColor(0, 245, 212, 100))
        painter.drawEllipse(QPointF(cx, cy), r_inner, r_inner)
        
        # Core
        painter.setBrush(QColor(255, 71, 87, 255))
        painter.drawEllipse(QPointF(cx, cy), r_core, r_core)
        painter.end()


class GazeTargetGame(QWidget):
    back_clicked = Signal()
    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self._audio = audio
        self._running = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.header = _ViewHeader("Gaze Target Precision")
        self.header.back_clicked.connect(self.back_clicked)
        self.header.reset_clicked.connect(self._reset_game)
        layout.addWidget(self.header)
        
        # 3-part Health/Score Bar
        score_layout = QHBoxLayout()
        score_layout.setContentsMargins(S(40), 0, S(40), 0)
        
        self._score_lbl = QLabel("Score: 0")
        self._score_lbl.setStyleSheet(f"color: #00D2FF; font-size: {S(18)}px; font-weight: bold;")
        score_layout.addWidget(self._score_lbl)
        
        self._status = QLabel("Targets: 0 / 10")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(18)}px; font-weight: bold;")
        score_layout.addWidget(self._status, 1)
        
        self._lives_lbl = QLabel("❤️ ❤️ ❤️")
        self._lives_lbl.setStyleSheet(f"color: #FF4757; font-size: {S(20)}px; font-weight: bold;")
        score_layout.addWidget(self._lives_lbl)
        
        layout.addLayout(score_layout)

        self._arena = QWidget()
        self._arena.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._arena.setStyleSheet(f"QWidget#arena {{ border: 0px solid #FF4757; }}")
        self._arena.setObjectName("arena")
        layout.addWidget(self._arena, 1)

        self._target = PrecisionTargetWidget(self._arena)
        self._target.hide()
        
        # End Game Overlay
        self._end_modal = QFrame(self._arena)
        self._end_modal.setStyleSheet(f"QFrame {{ background: {hex_to_rgba('#0E1E2E', 0.95)}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(20)}px; }}")
        self._end_modal.hide()
        
        modal_layout = QVBoxLayout(self._end_modal)
        modal_layout.setContentsMargins(S(40), S(40), S(40), S(40))
        modal_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._end_title = QLabel("")
        self._end_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        modal_layout.addWidget(self._end_title)
        
        self._end_stats = QLabel("")
        self._end_stats.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._end_stats.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(18)}px; margin-bottom: {S(20)}px; background: transparent; border: none;")
        modal_layout.addWidget(self._end_stats)
        
        self._end_score = QLabel("")
        self._end_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._end_score.setStyleSheet(f"color: #00D2FF; font-size: {S(64)}px; font-weight: 900; background: transparent; border: none; margin-bottom: {S(10)}px;")
        modal_layout.addWidget(self._end_score)
        
        self._end_badge = QLabel("")
        self._end_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._end_badge.setStyleSheet(f"color: #F59E0B; font-size: {S(24)}px; font-weight: bold; background: transparent; border: none; margin-bottom: {S(20)}px;")
        modal_layout.addWidget(self._end_badge)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(S(20))
        
        replay_btn = QPushButton("🔄 Try Again")
        replay_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        replay_btn.setFixedSize(S(200), S(60))
        replay_btn.setStyleSheet(f"background: {T('ACCENT')}; color: white; border-radius: {S(12)}px; font-size: {S(20)}px; font-weight: bold;")
        replay_btn.clicked.connect(self._reset_game)
        btn_layout.addWidget(replay_btn)
        
        back_btn = QPushButton("⬅️ Back to Games")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setFixedSize(S(240), S(60))
        back_btn.setStyleSheet(f"background: {T('BG_ELEVATED')}; color: {T('TEXT_PRIMARY')}; border: 2px solid {T('BORDER_SOLID')}; border-radius: {S(12)}px; font-size: {S(20)}px; font-weight: bold;")
        back_btn.clicked.connect(self.back_clicked)
        btn_layout.addWidget(back_btn)
        
        modal_layout.addLayout(btn_layout)
        
        self._timeout_timer = QTimer(self)
        self._timeout_timer.setSingleShot(True)
        self._timeout_timer.timeout.connect(self._on_timeout)
        
        self._floating_lbls = []
        
        # State
        self._score = 0
        self._targets_done = 0
        self._lives = 3
        self._bullseyes = 0
        self._displayed_score = 0
        self._roll_timer = QTimer(self)
        self._roll_timer.timeout.connect(self._roll_score)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._end_modal.isVisible():
            w = S(600)
            h = S(450)
            x = (self._arena.width() - w) // 2
            y = (self._arena.height() - h) // 2
            self._end_modal.setGeometry(x, y, w, h)

    def showEvent(self, event):
        self._reset_game()

    def hideEvent(self, event):
        self._running = False
        self._timeout_timer.stop()
        self._target.hide()

    def _reset_game(self):
        self._score = 0
        self._targets_done = 0
        self._lives = 3
        self._bullseyes = 0
        self._running = True
        self._end_modal.hide()
        self._update_ui()
        self._spawn_target()

    def _update_ui(self):
        self._score_lbl.setText(f"Score: {self._score}")
        self._status.setText(f"Targets: {self._targets_done} / 10")
        hearts = "❤️ " * self._lives + "💔 " * (3 - self._lives)
        self._lives_lbl.setText(hearts.strip())

    def _spawn_target(self):
        if not self._running: return
        w = self._arena.width()
        h = self._arena.height()
        if w < 100 or h < 100:
            QTimer.singleShot(100, self._spawn_target)
            return
            
        size = self._target.width()
        
        # Avoid bottom right (PiP) and top margins
        x = random.randint(S(20), max(S(20), w - size - S(20)))
        y = random.randint(S(20), max(S(20), h - size - S(20)))
        
        if x > w - S(300) and y > h - S(250):
            x = x - S(300)
            
        self._target.move(x, y)
        self._target.show()
        
        self._timeout_timer.start(5000)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.receive_blink()
        super().mousePressEvent(event)

    def receive_blink(self):
        if not self._running or not self._target.isVisible(): return
        
        cursor_pos = self._arena.mapFromGlobal(self._arena.cursor().pos())
        
        # Calculate distance
        cx = self._target.x() + self._target.width() / 2.0
        cy = self._target.y() + self._target.height() / 2.0
        
        import math
        dist = math.sqrt((cursor_pos.x() - cx)**2 + (cursor_pos.y() - cy)**2)
        
        self._timeout_timer.stop()
        self._target.hide()
        self._targets_done += 1
        
        d_scaled = dist / (S(1.0) if S(1.0) > 0 else 1.0)
        
        pts = 0
        txt = ""
        col = ""
        
        if d_scaled <= S(15):
            pts = 100
            txt = "+100 BULLSEYE!"
            col = "#FF4757"
            self._bullseyes += 1
            if self._audio: self._audio.core_hit()
        elif d_scaled <= S(35):
            pts = 50
            txt = "+50 GREAT!"
            col = "#00F5D4"
            if self._audio: self._audio.ring_hit()
        elif d_scaled <= S(60):
            pts = 25
            txt = "+25 OK!"
            col = "#00D2FF"
            if self._audio: self._audio.ring_hit()
        else:
            self._lose_life()
            return
            
        self._score += pts
        self._spawn_floating_text(txt, col, cursor_pos.x(), cursor_pos.y())
        self._update_ui()
        
        if self._targets_done >= 10:
            QTimer.singleShot(600, self._show_end_game)
        else:
            QTimer.singleShot(600, self._spawn_target)

    def _on_timeout(self):
        if not self._running or not self._target.isVisible(): return
        self._target.hide()
        self._targets_done += 1
        self._lose_life()

    def _lose_life(self):
        self._lives -= 1
        self._update_ui()
        if self._audio: self._audio.miss()
        
        self._arena.setStyleSheet(f"QWidget#arena {{ border: 4px solid #FF4757; }}")
        QTimer.singleShot(200, lambda: self._arena.setStyleSheet(f"QWidget#arena {{ border: 0px solid #FF4757; }}"))
        
        if self._lives <= 0 or self._targets_done >= 10:
            QTimer.singleShot(600, self._show_end_game)
        else:
            # 1.5 second breather requested before next target
            QTimer.singleShot(1500, self._spawn_target)

    def _spawn_floating_text(self, text, color, x, y):
        lbl = QLabel(text, self._arena)
        lbl.setStyleSheet(f"color: {color}; font-size: {S(24)}px; font-weight: bold; background: transparent;")
        lbl.move(x, y - S(30))
        lbl.show()
        
        anim1 = QPropertyAnimation(lbl, b"pos")
        anim1.setDuration(800)
        anim1.setStartValue(lbl.pos())
        anim1.setEndValue(lbl.pos() - QPoint(0, S(50)))
        anim1.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        anim1.finished.connect(lbl.deleteLater)
        anim1.start()
        self._floating_lbls.append((lbl, anim1))

    def _show_end_game(self):
        self._running = False
        self._timeout_timer.stop()
        self._target.hide()
        
        w = S(600)
        h = S(450)
        x = (self._arena.width() - w) // 2
        y = (self._arena.height() - h) // 2
        self._end_modal.setGeometry(x, y, w, h)
        
        title = "Game Over!" if self._lives <= 0 else "Mission Accomplished!"
        t_col = "#FF4757" if self._lives <= 0 else "#00D2FF"
        
        self._end_title.setText(title)
        self._end_title.setStyleSheet(f"color: {t_col}; font-size: {S(36)}px; font-weight: 900; background: transparent; border: none;")
        
        self._end_stats.setText(f"Bullseyes Hit: {self._bullseyes} | Total Targets: {self._targets_done} | Remaining Lives: {self._lives}")
        
        self._displayed_score = 0
        self._end_score.setText("0")
        self._end_badge.setText("")
        
        if self._audio: self._audio.victory_fanfare()
        
        self._end_modal.show()
        self._end_modal.raise_()
        
        self._roll_timer.start(30)  # 30ms ticks for roll-up

    def _roll_score(self):
        if self._displayed_score < self._score:
            self._displayed_score += max(1, self._score // 30)  # ~1 sec roll up
            if self._displayed_score > self._score:
                self._displayed_score = self._score
            self._end_score.setText(str(self._displayed_score))
        else:
            self._roll_timer.stop()
            
            badge = ""
            if self._score >= 800: badge = "🌟 Master Marksman"
            elif self._score >= 500: badge = "🎯 Sharp Observer"
            else: badge = "👍 Good Effort"
            
            self._end_badge.setText(badge)


# ---------------------------------------------------------------------------
# Section 2: Health Menu & Wellness
# ---------------------------------------------------------------------------

class _HealthMenu(QWidget):
    back_clicked = Signal()
    launch_activity = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.header = _ViewHeader("Health Activities", show_reset=False)
        self.header.back_clicked.connect(self.back_clicked)
        layout.addWidget(self.header)

        grid_w = QWidget()
        grid = QGridLayout(grid_w)
        grid.setContentsMargins(S(80), S(40), S(80), 200)
        grid.setSpacing(S(24))

        activities = [
            ("Paced Breathing", "4-4-6 or Box Breathing guide.", "\U0001f60c", "#10B981", 10),
            ("Muscle Relaxation", "Facial tension release via TTS.", "\U0001f9d8", "#8B5CF6", 11),
        ]
        for i, (t, d, ic, c, idx) in enumerate(activities):
            tile = _GameTile(t, d, ic, c)
            tile.clicked.connect(lambda checked=False, x=idx: self.launch_activity.emit(x))
            grid.addWidget(tile, i // 2, i % 2)
            
        layout.addWidget(grid_w, 1)


class _BreathingOrbWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(S(500), S(500))
        self._scale = 0.65
        self.phase_text = "REST"
        self.count_text = ""
        self.color_center = QColor(T("BG_ELEVATED"))
        self.color_edge = QColor(T("BG_DARK"))
        
        self.anim = QVariantAnimation(self)
        self.anim.valueChanged.connect(self._on_anim)
        
    def _on_anim(self, val):
        self._scale = val
        self.update()
        
    def set_colors(self, center, edge):
        self.color_center = QColor(center)
        self.color_edge = QColor(edge)
        self.update()
        
    def set_text(self, phase, count):
        self.phase_text = phase
        self.count_text = count
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx = self.width() / 2
        cy = self.height() / 2
        
        max_r = S(200)
        current_r = max_r * self._scale
        
        # Ripple rings
        painter.setPen(QPen(QColor(255,255,255, 20), S(2)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), current_r + S(20), current_r + S(20))
        painter.drawEllipse(QPointF(cx, cy), current_r + S(40), current_r + S(40))
        
        # Core Halo
        grad = QRadialGradient(cx, cy, current_r)
        grad.setColorAt(0.0, self.color_center)
        grad.setColorAt(1.0, self.color_edge)
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawEllipse(QPointF(cx, cy), current_r, current_r)
        
        # Text
        painter.setPen(QColor(255,255,255))
        f_phase = QFont("Segoe UI", S(24), QFont.Weight.Bold)
        f_phase.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.0)
        painter.setFont(f_phase)
        painter.drawText(QRectF(cx - max_r, cy - S(60), max_r*2, S(40)), Qt.AlignmentFlag.AlignCenter, self.phase_text)
        
        f_count = QFont("Segoe UI", S(64), QFont.Weight.Black)
        painter.setFont(f_count)
        painter.drawText(QRectF(cx - max_r, cy - S(20), max_r*2, S(80)), Qt.AlignmentFlag.AlignCenter, self.count_text)
        painter.end()

class PacedBreathingGuide(QWidget):
    back_clicked = Signal()
    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self._audio = audio
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.header = _ViewHeader("Paced Breathing")
        self.header.back_clicked.connect(self.back_clicked)
        self.header.reset_clicked.connect(self._reset)
        layout.addWidget(self.header)
        
        top_bar = QHBoxLayout()
        self._mode_btn = DwellButton("Mode: 4-4-6 Calming", dwell_ms=800)
        self._mode_btn.setFixedSize(S(240), S(44))
        self._mode = "446"
        self._mode_btn.clicked.connect(self._toggle_mode)
        top_bar.addStretch()
        top_bar.addWidget(self._mode_btn)
        
        self._cycle_badge = QLabel("Cycle 0 of 5 Completed")
        self._cycle_badge.setStyleSheet(f"background: {hex_to_rgba(T('ACCENT'), 0.2)}; color: {T('ACCENT')}; padding: {S(10)}px {S(20)}px; border-radius: {S(20)}px; font-weight: bold; font-size: {S(16)}px;")
        top_bar.addWidget(self._cycle_badge)
        top_bar.addStretch()
        
        layout.addLayout(top_bar)
        
        self._orb = _BreathingOrbWidget()
        layout.addWidget(self._orb, 1, Qt.AlignmentFlag.AlignCenter)
        
        self._start_btn = DwellButton("▶ Start Session", dwell_ms=800)
        self._start_btn.setFixedSize(S(250), S(60))
        self._start_btn.clicked.connect(self._start_session)
        layout.addWidget(self._start_btn, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(S(20))
        
        self._running = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        
        self._phase = "rest"
        self._ticks_left = 0
        self._cycles = 0
        
    def showEvent(self, event):
        ActivityLifecycleManager().register_timer(self._timer)
        ActivityLifecycleManager().register_anim(self._orb.anim)
        ActivityLifecycleManager().register_hook(self._reset)
        super().showEvent(event)

    def hideEvent(self, event):
        self._reset()
        super().hideEvent(event)

    def _toggle_mode(self):
        if self._running: return
        if self._mode == "446":
            self._mode = "box"
            self._mode_btn.setText("Mode: 4-4-4-4 Box")
        else:
            self._mode = "446"
            self._mode_btn.setText("Mode: 4-4-6 Calming")

    def _reset(self):
        self._running = False
        self._timer.stop()
        self._orb.anim.stop()
        self._orb._scale = 0.65
        self._orb.set_colors("#1E293B", "#0F172A")
        self._orb.set_text("REST", "")
        self._start_btn.setText("▶ Start Session")
        self._cycles = 0
        self._cycle_badge.setText("Cycle 0 of 5 Completed")

    def _start_session(self):
        if self._running:
            self._reset()
            return
        self._running = True
        self._start_btn.setText("⏹ Stop Session")
        self._cycles = 0
        self._cycle_badge.setText(f"Cycle {self._cycles} of 5 Completed")
        self._set_phase("inhale")

    def _set_phase(self, phase):
        if not self._running: return
        self._phase = phase
        
        if phase == "inhale":
            self._ticks_left = 4
            self._orb.set_colors("#00D2FF", "#00F5D4")
            self._orb.set_text("INHALE", str(self._ticks_left))
            if self._audio: self._audio.sweep_tone(220, 440, 4.0, 0.05)
            self._orb.anim.setDuration(4000)
            self._orb.anim.setStartValue(self._orb._scale)
            self._orb.anim.setEndValue(1.4)
            self._orb.anim.start()
            
        elif phase == "hold1":
            self._ticks_left = 4
            self._orb.set_colors("#FFA502", "#D97706")
            self._orb.set_text("HOLD", str(self._ticks_left))
            if self._audio: 
                self._audio.play_tone(440, 'sine', 4.0, 0.02)
                self._audio.play_tone(554, 'sine', 4.0, 0.02)
            
        elif phase == "exhale":
            self._ticks_left = 6 if self._mode == "446" else 4
            self._orb.set_colors("#0077B6", "#023E8A")
            self._orb.set_text("EXHALE", str(self._ticks_left))
            if self._audio: self._audio.sweep_tone(440, 220, float(self._ticks_left), 0.05)
            self._orb.anim.setDuration(self._ticks_left * 1000)
            self._orb.anim.setStartValue(self._orb._scale)
            self._orb.anim.setEndValue(0.65)
            self._orb.anim.start()
            
        elif phase == "hold2":
            self._ticks_left = 4
            self._orb.set_colors("#FFA502", "#D97706")
            self._orb.set_text("HOLD", str(self._ticks_left))
            if self._audio: 
                self._audio.play_tone(440, 'sine', 4.0, 0.02)
                self._audio.play_tone(554, 'sine', 4.0, 0.02)
                
        self._timer.start(1000)

    def _tick(self):
        if not self._running: return
        self._ticks_left -= 1
        if self._ticks_left > 0:
            self._orb.set_text(self._phase.upper().replace('1','').replace('2',''), str(self._ticks_left))
        else:
            self._timer.stop()
            # Next phase transition
            if self._phase == "inhale":
                self._set_phase("hold1")
            elif self._phase == "hold1":
                self._set_phase("exhale")
            elif self._phase == "exhale":
                if self._mode == "box":
                    self._set_phase("hold2")
                else:
                    self._cycles += 1
                    self._cycle_badge.setText(f"Cycle {self._cycles} of 5 Completed")
                    if self._cycles >= 5:
                        self._reset()
                    else:
                        self._set_phase("inhale")
            elif self._phase == "hold2":
                self._cycles += 1
                self._cycle_badge.setText(f"Cycle {self._cycles} of 5 Completed")
                if self._cycles >= 5:
                    self._reset()
                else:
                    self._set_phase("inhale")


class _FacialMuscleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(S(500), S(500))
        self.active_zone = -1  # -1 = none, 0 = brow, 1 = eyes, 2 = jaw, 3 = neck
        self.zone_color = QColor("#FFA502") # amber
        
    def set_zone(self, zone_idx, color_hex):
        self.active_zone = zone_idx
        self.zone_color = QColor(color_hex)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx = self.width() / 2
        cy = self.height() / 2
        
        # Base Silhouette (abstract oval head)
        painter.setPen(QPen(QColor(255,255,255, 40), S(4)))
        painter.setBrush(QColor(15, 23, 42, 200))
        head_rect = QRectF(cx - S(100), cy - S(150), S(200), S(280))
        painter.drawEllipse(head_rect)
        
        # Neck
        neck_rect = QRectF(cx - S(40), cy + S(120), S(80), S(60))
        painter.drawRoundedRect(neck_rect, S(10), S(10))
        
        # Draw active zone highlights
        if self.active_zone != -1:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.zone_color)
            
            # Glow effect
            c = QColor(self.zone_color)
            c.setAlpha(60)
            painter.setPen(QPen(c, S(15)))
            
            if self.active_zone == 0:
                # Brow
                painter.drawLine(cx - S(60), cy - S(70), cx + S(60), cy - S(70))
            elif self.active_zone == 1:
                # Eyes
                painter.drawEllipse(QPointF(cx - S(40), cy - S(30)), S(20), S(10))
                painter.drawEllipse(QPointF(cx + S(40), cy - S(30)), S(20), S(10))
            elif self.active_zone == 2:
                # Jaw
                path = QPainterPath()
                path.moveTo(cx - S(80), cy + S(50))
                path.quadTo(cx, cy + S(130), cx + S(80), cy + S(50))
                painter.drawPath(path)
            elif self.active_zone == 3:
                # Neck
                painter.drawRoundedRect(QRectF(cx - S(50), cy + S(130), S(100), S(40)), S(10), S(10))
                painter.end()


class FacialMuscleRelaxation(QWidget):
    back_clicked = Signal()
    def __init__(self, speech, parent=None):
        super().__init__(parent)
        self._speech = speech
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.header = _ViewHeader("Muscle Relaxation", show_reset=False)
        self.header.back_clicked.connect(self.back_clicked)
        layout.addWidget(self.header)
        
        self._instruction = QLabel("Facial Muscle Relaxation")
        self._instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._instruction.setWordWrap(True)
        self._instruction.setStyleSheet(f"color: {T('ACCENT')}; font-size: {S(32)}px; font-weight: bold;")
        self._instruction.setFixedHeight(S(80))
        layout.addWidget(self._instruction)
        
        self._face = _FacialMuscleWidget()
        layout.addWidget(self._face, 1, Qt.AlignmentFlag.AlignCenter)
        
        self._progress = QLabel("Step 0 of 4")
        self._progress.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(18)}px;")
        self._progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._progress)
        
        self._start_btn = DwellButton("▶ Start Guide", dwell_ms=800)
        self._start_btn.setFixedSize(S(250), S(60))
        self._start_btn.clicked.connect(self._start_guide)
        layout.addWidget(self._start_btn, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(S(20))
        
        self._running = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        
        self._step = 0
        self._phase = 0 # 0=awareness, 1=release, 2=transition
        self._ticks_left = 0
        
    def showEvent(self, event):
        ActivityLifecycleManager().register_timer(self._timer)
        ActivityLifecycleManager().register_hook(self._reset)
        super().showEvent(event)

    def hideEvent(self, event):
        self._reset()
        super().hideEvent(event)
        
    def _reset(self):
        self._running = False
        self._timer.stop()
        self._start_btn.setText("▶ Start Guide")
        self._instruction.setText("Facial Muscle Relaxation")
        self._progress.setText("Step 0 of 4")
        self._face.set_zone(-1, "#000000")

    def _start_guide(self):
        if self._running:
            self._reset()
            return
        self._running = True
        self._start_btn.setText("⏹ Stop Guide")
        self._step = 0
        self._set_phase(0)

    def _set_phase(self, phase):
        if not self._running: return
        self._phase = phase
        
        if phase == 0:
            # Awareness
            self._ticks_left = 3
            self._face.set_zone(self._step, "#FFA502")
            
            # Speak instructions
            steps = [
                "Focus on your forehead and eyebrows. Smooth out all tension. Let your brow completely unwrinkle.",
                "Gently close your eyes halfway. Relax the muscles around your eyelids and temples.",
                "Unclench your jaw. Part your teeth slightly and let your facial muscles drop completely loose.",
                "Drop your shoulders and ease your neck. Breathe out slowly and release all physical strain."
            ]
            self._instruction.setText(steps[self._step])
            if self._speech: self._speech.speak(steps[self._step])
            
        elif phase == 1:
            # Release
            self._ticks_left = 7
            self._face.set_zone(self._step, "#2ED573")
            
        elif phase == 2:
            # Transition
            self._ticks_left = 2
            self._face.set_zone(-1, "#000000")
            
        self._timer.start(1000)

    def _tick(self):
        if not self._running: return
        self._ticks_left -= 1
        
        if self._ticks_left > 0:
            pass
        else:
            self._timer.stop()
            if self._phase == 0:
                self._set_phase(1)
            elif self._phase == 1:
                self._set_phase(2)
            elif self._phase == 2:
                self._step += 1
                self._progress.setText(f"Step {self._step} of 4")
                if self._step >= 4:
                    # Completion Modal
                    self._instruction.setText("✨ Session Complete.\nYour ocular tracking is recalibrated and relaxed.")
                    self._start_btn.setText("🔄 Repeat Routine")
                    self._running = False
                else:
                    self._set_phase(0)


# ---------------------------------------------------------------------------
# Section 3: Music View
# ---------------------------------------------------------------------------

class SongCard(QWidget):
    clicked = Signal(str) # Emits track id
    def __init__(self, track, parent=None):
        super().__init__(parent)
        self.track = track
        self.setFixedSize(S(170), S(240))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Dwell progress
        self._dwell_ms = 900
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(self._dwell_ms)
        self._hover_timer.timeout.connect(self._do_click)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(self._dwell_ms)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(100.0)
        self._anim.valueChanged.connect(self._on_anim)

        self._progress = 0.0
        self._is_hovered = False
        
        # Load Cover
        self._cover = QPixmap(self.track['cover'])
        if self._cover.isNull():
            # Mock cover
            self._cover = QPixmap(S(140), S(140))
            self._cover.fill(QColor("#334155"))

    def _do_click(self):
        self.clicked.emit(self.track['id'])

    def mousePressEvent(self, event):
        self._do_click()

    def receive_blink(self):
        if self._is_hovered:
            self._do_click()

    def _on_anim(self, val: float) -> None:
        self._progress = val
        self.update()

    def enterEvent(self, event):
        self._is_hovered = True
        self._hover_timer.start()
        self._anim.start()
        self.update()

    def leaveEvent(self, event):
        self._is_hovered = False
        self._hover_timer.stop()
        self._anim.stop()
        self._progress = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Base Background
        c_bg = QColor(T("BG_PANEL"))
        c_bg.setAlpha(127)
        if self._is_hovered:
            painter.setPen(QPen(QColor("#00D2FF"), S(2)))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(c_bg)
        painter.drawRoundedRect(self.rect(), S(12), S(12))
        
        # Dwell fill
        if self._progress > 0:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 210, 255, 30))
            w = int(self.width() * (self._progress / 100.0))
            painter.drawRoundedRect(0, 0, w, self.height(), S(12), S(12))
        
        # Draw Cover
        c_size = S(140)
        c_x = (self.width() - c_size) // 2
        c_y = S(15)
        # We need a rounded clip path, but let's just draw scaled pixmap
        scaled_cover = self._cover.scaled(c_size, c_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(c_x, c_y, scaled_cover)
        
        # Hover Overlay Play Icon
        if self._is_hovered:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 150))
            painter.drawEllipse(c_x + c_size//2 - S(25), c_y + c_size//2 - S(25), S(50), S(50))
            
            painter.setBrush(QColor(T("TEXT_PRIMARY")))
            poly = [
                QPointF(c_x + c_size//2 - S(8), c_y + c_size//2 - S(12)),
                QPointF(c_x + c_size//2 + S(12), c_y + c_size//2),
                QPointF(c_x + c_size//2 - S(8), c_y + c_size//2 + S(12))
            ]
            painter.drawPolygon(poly)
            
        # Draw Texts
        f_title = QFont("Segoe UI", S(14), QFont.Weight.Bold)
        f_sub = QFont("Segoe UI", S(12))
        
        painter.setFont(f_title)
        painter.setPen(QColor(T("TEXT_ON_IMAGE")))
        painter.drawText(QRectF(S(15), c_y + c_size + S(10), self.width() - S(30), S(20)), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, self.track['title'])
        
        painter.setFont(f_sub)
        painter.setPen(QColor(T("TEXT_MUTED")))
        painter.drawText(QRectF(S(15), c_y + c_size + S(30), self.width() - S(30), S(20)), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, f"{self.track['artist']}")
        painter.end()

class MusicView(QWidget):
    back_clicked = Signal()
    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self._sys_audio = audio
        
        self.library = [
            {
                "category": "Global Hits",
                "tracks": [
                    {"id": "trk1", "title": "Wavin' Flag", "artist": "K'NAAN", "src": "assets/music/songs/K'NAAN - Wavin' Flag (Coca-Cola Celebration Mix).mp3", "cover": "assets/music/covers/wavin_flag.jpg"},
                    {"id": "trk2", "title": "Perfect", "artist": "Ed Sheeran", "src": "assets/music/songs/Ed Sheeran - Perfect.mp3", "cover": "assets/music/covers/perfect.jpg"}
                ]
            },
            {
                "category": "Local & Cinematic",
                "tracks": [
                    {"id": "trk3", "title": "Suzume ft. Toaka", "artist": "RADWIMPS", "src": "assets/music/songs/RADWIMPS - Suzume (Lyrics) ft. Toaka.mp3", "cover": "assets/music/covers/suzume.jpg"},
                    {"id": "trk4", "title": "AMAR SHONAR BANGLA", "artist": "National Anthem of Bangladesh", "src": "assets/music/songs/আমার সোনার বাংলা আমি তোমায় ভালোবাসি ｜ AMAR SHONAR BANGLA ｜ National Anthem of Bangladesh 🇧🇩.mp3", "cover": "assets/music/covers/amar_shonar_bangla.jpg"}
                ]
            }
        ]
        
        self.flat_playlist = []
        for cat in self.library:
            self.flat_playlist.extend(cat["tracks"])
            
        self.current_index = 0
        self.is_playing = False
        
        # Qt Audio Engine
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        
        self.player.positionChanged.connect(self._on_time_update)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        
        # Setup UI
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.header = _ViewHeader("🎵 Music Lounge", show_reset=False)
        self.header.back_clicked.connect(self.back_clicked)
        layout.addWidget(self.header)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"QScrollArea {{ border: none; background: transparent; }}")
        
        self.content_w = QWidget()
        self.content_layout = QVBoxLayout(self.content_w)
        # CRITICAL: Bottom padding 260px for PiP camera
        self.content_layout.setContentsMargins(S(40), S(20), S(40), S(260))
        
        self.song_cards = []
        for cat in self.library:
            cat_lbl = QLabel(cat["category"])
            cat_lbl.setStyleSheet(f"color: {T('ACCENT')}; font-size: {S(22)}px; font-weight: bold; margin-top: {S(20)}px;")
            self.content_layout.addWidget(cat_lbl)
            
            shelf_w = QWidget()
            shelf_l = QHBoxLayout(shelf_w)
            shelf_l.setContentsMargins(0,0,0,0)
            shelf_l.setSpacing(S(20))
            
            for trk in cat["tracks"]:
                card = SongCard(trk)
                card.clicked.connect(self._play_track)
                shelf_l.addWidget(card)
                self.song_cards.append(card)
                
            shelf_l.addStretch()
            self.content_layout.addWidget(shelf_w)
            
        self.content_layout.addStretch()
        self.scroll.setWidget(self.content_w)
        layout.addWidget(self.scroll, 1)
        
        # Docked Now-Playing
        self.dock = QWidget(self)
        self.dock.setFixedHeight(S(100))
        self.dock.setStyleSheet(f"background: {hex_to_rgba(T('BG_DARK'), 0.95)}; border-top: 1px solid {hex_to_rgba('#334155', 0.5)};")
        self.dock.hide() # Hidden initially
        
        dock_l = QHBoxLayout(self.dock)
        dock_l.setContentsMargins(S(30), 0, S(30), 0)
        
        self.np_cover = QLabel()
        self.np_cover.setFixedSize(S(60), S(60))
        dock_l.addWidget(self.np_cover)
        
        np_info = QVBoxLayout()
        self.np_title = QLabel("Title")
        self.np_title.setStyleSheet(f"color: white; font-weight: bold; font-size: {S(16)}px;")
        self.np_artist = QLabel("Artist")
        self.np_artist.setStyleSheet(f"color: #94A3B8; font-size: {S(14)}px;")
        np_info.addWidget(self.np_title)
        np_info.addWidget(self.np_artist)
        dock_l.addLayout(np_info)
        dock_l.addStretch()
        
        # Center controls
        self.prev_btn = DwellButton("⏮", dwell_ms=600)
        self.prev_btn.setFixedSize(S(60), S(60))
        self.prev_btn.clicked.connect(self._prev_track)
        
        self.play_btn = DwellButton("▶", dwell_ms=600)
        self.play_btn.setFixedSize(S(80), S(80))
        self.play_btn.setStyleSheet(f"DwellButton {{ border-radius: {S(40)}px; background: {T('ACCENT')}; color: white; font-size: {S(30)}px; }}")
        self.play_btn.clicked.connect(self._toggle_play)
        
        self.next_btn = DwellButton("⏭", dwell_ms=600)
        self.next_btn.setFixedSize(S(60), S(60))
        self.next_btn.clicked.connect(self._next_track)
        
        dock_l.addWidget(self.prev_btn)
        dock_l.addSpacing(S(20))
        dock_l.addWidget(self.play_btn)
        dock_l.addSpacing(S(20))
        dock_l.addWidget(self.next_btn)
        dock_l.addStretch()
        
        # Progress
        self.time_lbl = QLabel("00:00 / 00:00")
        self.time_lbl.setStyleSheet(f"color: #94A3B8; font-family: monospace; font-size: {S(14)}px;")
        dock_l.addWidget(self.time_lbl)
        
        # Absolute positioning for dock at bottom (above PIP padding)
        # We will resize it in resizeEvent
        
        self._duration = 0

    def receive_blink(self):
        for card in self.song_cards:
            if getattr(card, '_is_hovered', False):
                card.receive_blink()
                return

    def _play_track(self, track_id):
        idx = next((i for i, t in enumerate(self.flat_playlist) if t['id'] == track_id), -1)
        if idx == -1: return
        self.current_index = idx
        track = self.flat_playlist[idx]
        
        self.np_title.setText(track['title'])
        self.np_artist.setText(track['artist'])
        pix = QPixmap(track['cover'])
        if pix.isNull():
            pix = QPixmap(S(60), S(60))
            pix.fill(QColor("#334155"))
        self.np_cover.setPixmap(pix.scaled(S(60), S(60), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        
        abs_path = os.path.abspath(track['src'])
        self.player.setSource(QUrl.fromLocalFile(abs_path))
        self.player.play()
        self.is_playing = True
        self.play_btn.setText("⏸")
        self.dock.show()

    def _toggle_play(self):
        if not self.player.source() and len(self.flat_playlist) > 0:
            self._play_track(self.flat_playlist[0]['id'])
            return
            
        if self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.play_btn.setText("▶")
        else:
            self.player.play()
            self.is_playing = True
            self.play_btn.setText("⏸")

    def _prev_track(self):
        if self.player.position() > 3000:
            self.player.setPosition(0)
        else:
            self.current_index = (self.current_index - 1) % len(self.flat_playlist)
            self._play_track(self.flat_playlist[self.current_index]['id'])

    def _next_track(self):
        self.current_index = (self.current_index + 1) % len(self.flat_playlist)
        self._play_track(self.flat_playlist[self.current_index]['id'])

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._next_track()

    def _on_duration_changed(self, dur):
        self._duration = dur

    def _on_time_update(self, pos):
        if self._duration > 0:
            cm = (pos // 1000) // 60
            cs = (pos // 1000) % 60
            dm = (self._duration // 1000) // 60
            ds = (self._duration // 1000) % 60
            self.time_lbl.setText(f"{cm:02d}:{cs:02d} / {dm:02d}:{ds:02d}")
            # Could also draw progress bar across the top of dock using QPainter later if needed

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.dock.setGeometry(0, self.height() - self.dock.height(), self.width(), self.dock.height())

    def _stop_all(self):
        self.player.stop()
        self.is_playing = False
        self.play_btn.setText("▶")
        self.dock.hide()
        self.time_lbl.setText("00:00 / 00:00")

    def showEvent(self, event):
        ActivityLifecycleManager().register_hook(self._stop_all)
        super().showEvent(event)

    def hideEvent(self, event):
        self._stop_all()
        super().hideEvent(event)

# ---------------------------------------------------------------------------
# Section 4: Creative Studio View
# ---------------------------------------------------------------------------

class CreativeStudioView(QWidget):
    back_clicked = Signal()
    def __init__(self, audio, parent=None):
        super().__init__(parent)
        self._audio = audio
        self._color = QColor("#00D2FF")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.header = _ViewHeader("Eye-Art Canvas")
        self.header.back_clicked.connect(self.back_clicked)
        self.header.reset_clicked.connect(self._clear_canvas)
        layout.addWidget(self.header)
        
        # Color palette below header
        palette = QFrame()
        palette.setFixedHeight(S(60))
        palette.setStyleSheet(f"background: {T('BG_CARD')}; border-bottom: 1px solid {T('BORDER_SOLID')};")
        p_layout = QHBoxLayout(palette)
        colors = ["#00D2FF", "#FF00FF", "#FFFF00", "#00FF00", "#FFFFFF"]
        for c in colors:
            btn = DwellButton("", dwell_ms=600)
            btn.setFixedSize(S(40), S(40))
            btn.setStyleSheet(f"background: {c}; border-radius: {S(20)}px;")
            btn.clicked.connect(lambda checked=False, col=c: self._set_color(col))
            p_layout.addWidget(btn)
        p_layout.addStretch(1)
        layout.addWidget(palette)
        
        self._canvas_lbl = QLabel()
        self._canvas_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._canvas_lbl, 1)
        
        self._pixmap = QPixmap(1920, 1080)
        self._pixmap.fill(QColor(T('BG_DARK')))
        self._canvas_lbl.setPixmap(self._pixmap)
        self._last_pos = None

    def _set_color(self, c):
        self._color = QColor(c)
        if self._audio: self._audio.ui_click()

    def _clear_canvas(self):
        self._pixmap.fill(QColor(T('BG_DARK')))
        self._canvas_lbl.setPixmap(self._pixmap)
        if self._audio: self._audio.ui_click()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if self._last_pos:
            painter = QPainter(self._pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(self._color, S(6), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(self._last_pos, pos)
            painter.end()
            self._canvas_lbl.setPixmap(self._pixmap)
        self._last_pos = pos

    def enterEvent(self, event):
        self._last_pos = None


# ---------------------------------------------------------------------------
# Top-level EntertainmentWidget
# ---------------------------------------------------------------------------

class EntertainmentWidget(QWidget):
    def __init__(self, tracker=None, speech=None, audio=None, parent=None) -> None:
        super().__init__(parent)
        self._tracker = tracker
        self._speech = speech
        self._audio = audio
        
        self._build_ui()
        if tracker is not None:
            tracker.blink_detected.connect(self.receive_blink)
        log.info("EntertainmentWidget initialised (v2.2 Architecture)")

    def receive_blink(self) -> None:
        idx = self._stack.currentIndex()
        if idx == 3: self._music.receive_blink()
        elif idx == 5: self._memory.receive_blink()
        elif idx == 6: self._tictactoe.receive_blink()
        elif idx == 7: self._target.receive_blink()
        elif idx == 8: self._bubble.receive_blink()
        elif idx == 9: self._simon.receive_blink()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = FadingStackedWidget()
        layout.addWidget(self._stack)

        # 0: MainMenu (2x2)
        self._main = _MainMenu()
        self._main.nav_games.connect(lambda: self._navigate_to(1))
        self._main.nav_health.connect(lambda: self._navigate_to(2))
        self._main.nav_music.connect(lambda: self._navigate_to(3))
        self._main.nav_studio.connect(lambda: self._navigate_to(4))
        self._stack.addWidget(self._main)
        
        # 1: Games Menu
        self._games_menu = _GamesMenu()
        self._games_menu.back_clicked.connect(lambda: self._navigate_to(0))
        self._games_menu.launch_game.connect(self._navigate_to)
        self._stack.addWidget(self._games_menu)

        # 2: Health Menu
        self._health_menu = _HealthMenu()
        self._health_menu.back_clicked.connect(lambda: self._navigate_to(0))
        self._health_menu.launch_activity.connect(self._navigate_to)
        self._stack.addWidget(self._health_menu)

        # 3: Music View
        self._music = MusicView(self._audio)
        self._music.back_clicked.connect(lambda: self._navigate_to(0))
        self._stack.addWidget(self._music)

        # 4: Creative View
        self._studio = CreativeStudioView(self._audio)
        self._studio.back_clicked.connect(lambda: self._navigate_to(0))
        self._stack.addWidget(self._studio)

        # Games (5-9)
        self._memory = MemoryMatchGame(self._audio)
        self._memory.back_clicked.connect(lambda: self._navigate_to(1))
        self._stack.addWidget(self._memory) # 5
        
        self._tictactoe = TicTacToeGame(self._audio)
        self._tictactoe.back_clicked.connect(lambda: self._navigate_to(1))
        self._stack.addWidget(self._tictactoe) # 6
        
        self._target = GazeTargetGame(self._audio)
        self._target.back_clicked.connect(lambda: self._navigate_to(1))
        self._stack.addWidget(self._target) # 7
        
        self._bubble = ZenBubblePopGame(self._audio)
        self._bubble.back_clicked.connect(lambda: self._navigate_to(1))
        self._stack.addWidget(self._bubble) # 8
        
        self._simon = SimonSequenceGame(self._audio)
        self._simon.back_clicked.connect(lambda: self._navigate_to(1))
        self._stack.addWidget(self._simon) # 9

        # Health (10-11)
        self._breathing = PacedBreathingGuide(self._audio)
        self._breathing.back_clicked.connect(lambda: self._navigate_to(2))
        self._stack.addWidget(self._breathing) # 10
        
        self._muscle = FacialMuscleRelaxation(self._speech)
        self._muscle.back_clicked.connect(lambda: self._navigate_to(2))
        self._stack.addWidget(self._muscle) # 11

    def _navigate_to(self, idx: int) -> None:
        ActivityLifecycleManager().stop_all(self._audio, self._speech)
        if self._audio: self._audio.ui_click()
        self._stack.setCurrentIndex(idx)
