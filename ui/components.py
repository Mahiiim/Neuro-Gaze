"""
ui/components.py
----------------
Shared, accessible UI components for Neuro-Gaze.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QPushButton, QStackedWidget, QGraphicsOpacityEffect

from ui.theme import T, S


class DwellButton(QPushButton):
    """
    A button that triggers a click automatically after the user hovers over it
    for a specified duration (dwell time). It provides visual feedback by filling
    up a background progress bar.
    """

    def __init__(self, text: str, dwell_ms: int = 600, parent=None) -> None:
        super().__init__(text, parent)
        self.setMinimumHeight(S(56))

        self._dwell_ms = dwell_ms
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(self._dwell_ms)
        self._hover_timer.timeout.connect(self.click)

        self._anim = QVariantAnimation(self)
        self._anim.setDuration(self._dwell_ms)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(100.0)
        self._anim.valueChanged.connect(self._on_anim)

        self._progress = 0.0
        self._is_active = False

    def set_active(self, active: bool) -> None:
        """
        Used for navigation buttons to mark them as the current page.
        When active, the progress bar is disabled.
        """
        self._is_active = active
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_anim(self, val: float) -> None:
        self._progress = val
        self.update()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        if not self._is_active:
            self._hover_timer.start()
            self._anim.start()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._hover_timer.stop()
        self._anim.stop()
        self._progress = 0.0
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self._progress > 0 and not self._is_active:
            painter = QPainter(self)
            painter.setPen(Qt.PenStyle.NoPen)
            # Read accent from live theme so the fill colour updates on switch
            painter.setBrush(QColor(T("ACCENT_HOVER")))
            painter.setOpacity(0.2)
            w = int(self.width() * (self._progress / 100.0))
            painter.drawRoundedRect(0, 0, w, self.height(), S(12), S(12))
            painter.end()


class FadingStackedWidget(QStackedWidget):
    """
    A QStackedWidget that performs a smooth opacity crossfade when the index changes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._fade_duration = 200
        self._next_index = -1
        
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(self._fade_duration)
        self._anim.valueChanged.connect(self._effect.setOpacity)
        self._anim.finished.connect(self._on_anim_finished)
        
        self._state = 'idle'

    def setCurrentIndex(self, index: int) -> None:
        if index == self.currentIndex() or self._state != 'idle':
            return
            
        self._state = 'fading_out'
        self._next_index = index
        
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()

    def _on_anim_finished(self):
        if self._state == 'fading_out':
            if self._next_index != -1:
                super().setCurrentIndex(self._next_index)
                self._next_index = -1
                
            self._state = 'fading_in'
            self._anim.setStartValue(0.0)
            self._anim.setEndValue(1.0)
            self._anim.start()
            
        elif self._state == 'fading_in':
            self._state = 'idle'
