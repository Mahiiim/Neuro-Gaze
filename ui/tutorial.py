"""
ui/tutorial.py
---------------
Interactive Guided Tutorial Engine
Provides a 5-step spotlight walkthrough highlighting essential features.
"""

from PySide6.QtCore import Qt, QRect, QPoint, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPainterPath
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame

from ui.theme import T, S, hex_to_rgba

class TutorialOverlay(QWidget):
    finished = Signal()
    step_changed = Signal(int)

    def __init__(self, parent: QWidget):
        # We assume parent is MainWindow
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self.hide()

        self._steps = []
        self._current_step_idx = 0
        self._target_rect = QRect()

        self._build_tooltip()

    def _build_tooltip(self):
        self.tooltip = QFrame(self)
        self.tooltip.setMaximumWidth(S(320))
        # Simulated glassmorphism tooltip
        bg = hex_to_rgba("#101F30", 0.9)
        border = hex_to_rgba("#00F5D4", 0.3)
        self.tooltip.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {S(12)}px;
            }}
        """)
        layout = QVBoxLayout(self.tooltip)
        layout.setContentsMargins(S(20), S(20), S(20), S(20))
        layout.setSpacing(S(12))

        self.lbl_progress = QLabel("Step 1 of 5")
        self.lbl_progress.setStyleSheet(f"color: {T('ACCENT')}; font-size: {S(12)}px; font-weight: bold; border: none;")
        layout.addWidget(self.lbl_progress)

        self.lbl_message = QLabel()
        self.lbl_message.setWordWrap(True)
        self.lbl_message.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(14)}px; line-height: 1.5; border: none; background: transparent;")
        layout.addWidget(self.lbl_message)

        # Progress bar
        self.progress_bar = QFrame()
        self.progress_bar.setFixedHeight(S(4))
        self.progress_bar.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(self.progress_bar)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0,0,0,0)

        self.btn_skip = QPushButton("Skip Tour")
        self.btn_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_skip.setStyleSheet(f"color: {T('TEXT_MUTED')}; background: transparent; border: none; text-decoration: underline; font-size: {S(13)}px;")
        self.btn_skip.clicked.connect(self.stop)
        btn_layout.addWidget(self.btn_skip)

        btn_layout.addStretch()

        self.btn_back = QPushButton("Back")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; background: {hex_to_rgba('#FFFFFF', 0.1)}; border: none; padding: {S(6)}px {S(12)}px; border-radius: {S(4)}px;")
        self.btn_back.clicked.connect(self.prev_step)
        btn_layout.addWidget(self.btn_back)

        self.btn_next = QPushButton("OK / Next")
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setStyleSheet(f"color: #000; background: {T('ACCENT_HOVER')}; border: none; font-weight: bold; padding: {S(6)}px {S(12)}px; border-radius: {S(4)}px;")
        self.btn_next.clicked.connect(self.next_step)
        btn_layout.addWidget(self.btn_next)

        layout.addLayout(btn_layout)

    def set_steps(self, steps):
        """
        steps is a list of dicts:
        {
            'targets': [QWidget, ...],
            'message': str,
            'on_enter': callable (optional, e.g., to navigate to a page)
        }
        """
        self._steps = steps

    def start(self):
        if not self._steps:
            return
        self.resize(self.parentWidget().size())
        self.raise_()
        self.show()
        self._current_step_idx = 0
        self._load_step()

    def stop(self):
        self.hide()
        self.finished.emit()

    def next_step(self):
        if self._current_step_idx < len(self._steps) - 1:
            self._current_step_idx += 1
            self._load_step()
        else:
            self.stop()

    def prev_step(self):
        if self._current_step_idx > 0:
            self._current_step_idx -= 1
            self._load_step()

    def _load_step(self):
        step = self._steps[self._current_step_idx]
        if 'on_enter' in step and step['on_enter']:
            step['on_enter']()

        self.lbl_progress.setText(f"Step {self._current_step_idx + 1} of {len(self._steps)}")
        self.lbl_message.setText(step['message'])

        if self._current_step_idx == 0:
            self.btn_back.hide()
        else:
            self.btn_back.show()

        if self._current_step_idx == len(self._steps) - 1:
            self.btn_next.setText("Finish")
        else:
            self.btn_next.setText("OK / Next")

        self._update_target()

    def _update_target(self):
        step = self._steps[self._current_step_idx]
        self._target_rects = []
        
        targets = step.get('targets', [])
        if 'target_widget' in step and step['target_widget']:
            targets.append(step['target_widget'])
            
        for widget in targets:
            if widget and widget.isVisible():
                global_pos = widget.mapToGlobal(QPoint(0, 0))
                local_pos = self.mapFromGlobal(global_pos)
                self._target_rects.append(QRect(local_pos, widget.size()))

        if not self._target_rects:
            # fallback if invisible
            self._target_rects.append(QRect(self.width()//2 - 100, self.height()//2 - 100, 200, 200))

        # Reposition tooltip
        self.tooltip.adjustSize()
        tt_w = self.tooltip.width()
        tt_h = self.tooltip.height()

        # Try to place it alongside the first target
        first_rect = self._target_rects[0]
        x = first_rect.right() + S(20)
        y = first_rect.center().y() - tt_h // 2

        # constrain to screen bounds
        if x + tt_w > self.width() - S(20): 
            x = first_rect.left() - tt_w - S(20)
        if x < S(20): x = S(20)

        if y < S(20): y = S(20)
        if y + tt_h > self.height() - S(20):
            y = self.height() - tt_h - S(20)
        
        self.tooltip.move(x, y)
        self.update()

    def resizeEvent(self, event):
        if self.isVisible():
            self.resize(self.parentWidget().size())
            self._update_target()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dim entire screen
        bg_path = QPainterPath()
        bg_path.addRect(self.rect())

        # Punch hole for target
        hole_path = QPainterPath()
        
        for r in getattr(self, '_target_rects', []):
            # Enlarge rect slightly for breathing room
            adj_r = r.adjusted(-S(8), -S(8), S(8), S(8))
            hole_path.addRoundedRect(adj_r, S(8), S(8))

        # subtract hole from background
        bg_path = bg_path.subtracted(hole_path)

        painter.fillPath(bg_path, QColor(6, 11, 16, 224)) # rgba(6, 11, 16, 0.88)

        # Glowing neon border around hole
        pen = QPen(QColor(0, 245, 212, 200)) # #00F5D4
        pen.setWidth(2)
        glow_pen = QPen(QColor(0, 245, 212, 60))
        glow_pen.setWidth(6)

        for r in getattr(self, '_target_rects', []):
            adj_r = r.adjusted(-S(8), -S(8), S(8), S(8))
            painter.setPen(pen)
            painter.drawRoundedRect(adj_r, S(8), S(8))
            painter.setPen(glow_pen)
            painter.drawRoundedRect(adj_r, S(8), S(8))
