"""
ui/about.py
------------
Next-Gen "About" Ecosystem Hub
Futuristic cyber-medical showcase utilizing glassmorphism approximations, 
interactive glow mechanics, staggered entrance transitions, and animated metrics.
"""

from __future__ import annotations

import math
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QPoint, QRect, QEvent, Signal
from PySide6.QtGui import QPainter, QColor, QRadialGradient, QBrush, QPen, QPainterPath, QPixmap, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QGraphicsOpacityEffect, QGridLayout, QPushButton, QSizePolicy, QApplication, QGraphicsDropShadowEffect,
    QScrollArea
)

from ui.theme import T, S, theme_manager, hex_to_rgba

class GlowCard(QFrame):
    """
    A custom frame that tracks the mouse and draws a radial gradient glow behind its content,
    simulating a glassmorphism/neon effect.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self._mouse_pos = QPoint(-1000, -1000)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        
        # We don't use stylesheets for background/border because we paint it manually
        self.setStyleSheet("background: transparent; border: none;")

    def enterEvent(self, event):
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._mouse_pos = QPoint(-1000, -1000)
        self.update()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        self._mouse_pos = event.position().toPoint()
        self.update()
        super().mouseMoveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(rect, S(12), S(12))

        # Base semi-translucent obsidian glass background
        painter.fillPath(path, QColor(T("BG_PANEL")).toRgb()) # rgba(16, 31, 48, 0.65)

        # Mouse tracking radial gradient
        if self._mouse_pos.x() > -1000:
            grad = QRadialGradient(self._mouse_pos, 400)
            # rgba(0,210,255,0.08)
            accent = QColor(T("ACCENT"))
            grad.setColorAt(0, QColor(accent.red(), accent.green(), accent.blue(), 20))
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            painter.fillPath(path, QBrush(grad))

        # Specular border
        accent_border = QColor(T("ACCENT"))
        pen = QPen(QColor(accent_border.red(), accent_border.green(), accent_border.blue(), 40))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawPath(path)

class AnimatedMetric(QWidget):
    """A chip showing a live spec metric with an optional pulsing dot."""
    def __init__(self, title: str, value: str, color_token: str, pulse: bool = False, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(S(12), S(12), S(12), S(12))
        layout.setSpacing(S(4))
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {T('TEXT_MUTED')}; font-size: {S(11)}px; font-weight: bold; letter-spacing: 1px; text-transform: uppercase;")
        layout.addWidget(title_lbl)

        val_layout = QHBoxLayout()
        val_layout.setContentsMargins(0, 0, 0, 0)
        val_layout.setSpacing(S(8))

        if pulse:
            self._dot = QLabel("●")
            self._dot.setStyleSheet(f"color: {T(color_token)}; font-size: {S(14)}px;")
            val_layout.addWidget(self._dot)
            # Simple visibility pulse
            self._pulse_timer = QTimer(self)
            self._pulse_timer.setInterval(800)
            self._pulse_timer.timeout.connect(self._toggle_pulse)
            self._pulse_timer.start()
            self._dot_visible = True

        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(16)}px; font-weight: 800;")
        val_layout.addWidget(val_lbl)
        val_layout.addStretch()

        layout.addLayout(val_layout)

    def _toggle_pulse(self):
        self._dot_visible = not self._dot_visible
        self._dot.setHidden(not self._dot_visible)

class AnimatedContainer(QWidget):
    """Wrapper that manages staggered entrance animation (Opacity)."""
    def __init__(self, child: QWidget, parent=None):
        super().__init__(parent)
        self.child = child
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(child)
        
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.effect.setOpacity(0.0)

    def start_anim(self, delay_ms: int):
        # Opacity animation
        self.op_anim = QPropertyAnimation(self.effect, b"opacity")
        self.op_anim.setDuration(600)
        self.op_anim.setStartValue(0.0)
        self.op_anim.setEndValue(1.0)
        self.op_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Timer to stagger the start
        QTimer.singleShot(delay_ms, self.op_anim.start)

class AboutWidget(QWidget):
    """Next-Gen 'About' Ecosystem Hub."""

    launch_tutorial_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        self._apply_theme()
        theme_manager().theme_changed.connect(self._apply_theme)

    def _build_ui(self) -> None:
        # Radial gradient background is applied in paintEvent
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 8px; background: transparent; margin: 0px; }
            QScrollBar::handle:vertical { background: rgba(0, 210, 255, 0.25); border-radius: 4px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background: rgba(0, 210, 255, 0.5); }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)

        container = QWidget()
        container.setObjectName("aboutContainer")
        container.setStyleSheet("QWidget#aboutContainer { background: transparent; }")

        self.main_layout = QVBoxLayout(container)
        self.main_layout.setContentsMargins(S(32), S(24), S(32), S(240))
        self.main_layout.setSpacing(S(24))

        self.cards: list[AnimatedContainer] = []

        # 1. Hero Identity Banner
        self._build_hero()

        # Tutorial Button
        btn_layout = QHBoxLayout()
        self.btn_tutorial = QPushButton("🎓 Launch Tutorial")
        self.btn_tutorial.setStyleSheet(f"background: {hex_to_rgba(T('ACCENT'), 0.1)}; border: 1px solid {T('ACCENT')}; color: {T('ACCENT')}; padding: {S(8)}px {S(16)}px; border-radius: {S(8)}px; font-weight: bold; font-size: {S(13)}px;")
        self.btn_tutorial.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tutorial.clicked.connect(self.launch_tutorial_requested.emit)
        self.btn_tutorial.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn_layout.addWidget(self.btn_tutorial)
        btn_layout.addStretch(1)
        self.main_layout.addLayout(btn_layout)

        # 2. Interactive About Card
        self._build_research(self.main_layout)
        
        # 3. Developer & Contact Showcase Card
        self._build_developer(self.main_layout)
        
        self.main_layout.addStretch(1)

        scroll_area.setWidget(container)
        outer_layout.addWidget(scroll_area)

    def _add_animated_card(self, widget: QWidget, layout) -> None:
        container = AnimatedContainer(widget)
        layout.addWidget(container)
        self.cards.append(container)

    def _build_hero(self) -> None:
        card = GlowCard()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(S(30), S(30), S(30), S(30))
        layout.setSpacing(S(20))

        # Logo with rotating reticle (simulated with standard pixmap for now)
        logo_container = QWidget()
        logo_container.setFixedSize(S(100), S(100))
        # Drop shadow for pulse
        self.logo_shadow = QGraphicsDropShadowEffect()
        self.logo_shadow.setBlurRadius(25)
        c = QColor(T("ACCENT_HOVER"))
        c.setAlphaF(0.35)
        self.logo_shadow.setColor(c)
        self.logo_shadow.setOffset(0, 0)
        
        logo_lbl = QLabel(logo_container)
        logo_lbl.setFixedSize(S(100), S(100))
        pix = QPixmap("assets/logo.jpg").scaled(S(100), S(100), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        # Create circular mask
        mask = QPixmap(S(100), S(100))
        mask.fill(Qt.GlobalColor.transparent)
        p = QPainter(mask)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(Qt.GlobalColor.black)
        p.drawEllipse(0, 0, S(100), S(100))
        p.end()
        pix.setMask(mask.createHeuristicMask())

        logo_lbl.setPixmap(pix)
        logo_lbl.setGraphicsEffect(self.logo_shadow)
        
        # Pulsing animation for shadow
        self.shadow_anim = QPropertyAnimation(self.logo_shadow, b"blurRadius")
        self.shadow_anim.setDuration(2000)
        self.shadow_anim.setStartValue(25)
        self.shadow_anim.setEndValue(45)
        self.shadow_anim.setLoopCount(-1) # infinite
        self.shadow_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.shadow_anim.start()

        layout.addWidget(logo_container)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(S(8))

        title = QLabel("NEURO-GAZE")
        title.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(36)}px; font-weight: 900; letter-spacing: 4px;")
        # Give title a text-shadow equivalent using QGraphicsDropShadowEffect
        title_shadow = QGraphicsDropShadowEffect()
        title_shadow.setBlurRadius(10)
        c2 = QColor(T("ACCENT"))
        c2.setAlphaF(0.4)
        title_shadow.setColor(c2)
        title_shadow.setOffset(0, 0)
        title.setGraphicsEffect(title_shadow)
        text_layout.addWidget(title)

        badge = QLabel(" v1.2.0-Alpha • Core Engine Active ")
        badge.setStyleSheet(f"background: {hex_to_rgba('#00F5D4', 0.15)}; color: {T('ACCENT_HOVER')}; border: 1px solid {hex_to_rgba('#00F5D4', 0.4)}; border-radius: {S(12)}px; font-size: {S(11)}px; font-weight: bold; padding: {S(4)}px;")
        badge.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        text_layout.addWidget(badge)

        subtitle = QLabel("Next-Generation Multi-Modal Assistive Ecosystem for Locked-In Syndrome Autonomy")
        subtitle.setStyleSheet(f"color: {T('TEXT_MUTED')}; font-size: {S(14)}px;")
        text_layout.addWidget(subtitle)

        layout.addLayout(text_layout)
        layout.addStretch(1)

        self._add_animated_card(card, self.main_layout)



    def _build_research(self, parent_layout) -> None:
        card = GlowCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(S(24), S(24), S(24), S(24))
        layout.setSpacing(S(16))

        header = QLabel("About Neuro-Gaze")
        header.setStyleSheet(f"color: {T('ACCENT')}; font-size: {S(20)}px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(header)

        desc = QLabel("Neuro-Gaze is an integrated assistive ecosystem engineered specifically for individuals living with Locked-in Syndrome (LIS), ALS, and severe motor paralysis. The platform restores personal independence by translating non-invasive facial orientation and eye movements into real-world actions without requiring wearable sensors or invasive implants.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(15)}px; line-height: 1.6;")
        layout.addWidget(desc)

        specs_header = QLabel("Core Modules Summary:")
        specs_header.setStyleSheet(f"color: {T('TEXT_MUTED')}; font-size: {S(14)}px; font-weight: bold; margin-top: {S(10)}px;")
        layout.addWidget(specs_header)

        specs_text = (
            "• Adaptive Wheelchair Navigation: Gaze-directed motor steering equipped with dual front and rear ultrasonic obstacle avoidance operating at a calibrated 45 cm safety stop threshold.\n\n"
            "• Environmental IoT Control: Dedicated dual-state (ON/OFF) relay switching for household appliances (lights, fans) communicating over an isolated local Wi-Fi link.\n\n"
            "• Augmentative & Alternative Communication (AAC): Real-time gaze-controlled virtual keyboard and quick-phrase system backed by text-to-speech voice synthesis.\n\n"
            "• Safety & Caregiver Alerting: Zero-cloud local acoustic distress sirens and caregiver summon tools ensuring immediate attention even without internet connectivity."
        )
        specs = QLabel(specs_text)
        specs.setWordWrap(True)
        specs.setStyleSheet(f"color: {T('TEXT_MUTED')}; font-size: {S(14)}px; line-height: 1.5;")
        layout.addWidget(specs)
        layout.addStretch(1)

        self._add_animated_card(card, parent_layout)

    def _build_developer(self, parent_layout) -> None:
        card = GlowCard()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(S(24), S(24), S(24), S(24))
        layout.setSpacing(S(16))

        header = QLabel("Developer Showcase")
        header.setStyleSheet(f"color: {T('ACCENT_HOVER')}; font-size: {S(18)}px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(header)

        dev_grid = QGridLayout()
        dev_grid.setVerticalSpacing(S(12))
        dev_grid.setHorizontalSpacing(S(16))

        def add_row(r, label, value):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {T('TEXT_MUTED')}; font-size: {S(12)}px; font-weight: bold;")
            val = QLabel(value)
            val.setStyleSheet(f"color: {T('TEXT_PRIMARY')}; font-size: {S(14)}px;")
            dev_grid.addWidget(lbl, r, 0)
            dev_grid.addWidget(val, r, 1)

        add_row(0, "Lead Developer:", "Neuro-Gaze Research Team")
        add_row(1, "Affiliation:", "Open Source Accessibility Lab")

        layout.addLayout(dev_grid)

        # Email Display
        self.lbl_email = QLabel("📧 mohaiminul118@gmail.com")
        self.lbl_email.setStyleSheet(f"color: {T('ACCENT')}; font-size: {S(14)}px; font-weight: bold; background: {hex_to_rgba(T('ACCENT'), 0.1)}; border: 1px solid {T('ACCENT')}; padding: {S(10)}px; border-radius: {S(8)}px;")
        self.lbl_email.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_email.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.lbl_email)

        # Docs Button
        btn_docs = QPushButton("📄 System Documentation ↗")
        btn_docs.setStyleSheet(f"background: {hex_to_rgba('#FFFFFF', 0.05)}; border: 1px solid {hex_to_rgba('#FFFFFF', 0.2)}; color: {T('TEXT_PRIMARY')}; padding: {S(10)}px; border-radius: {S(8)}px; font-weight: bold;")
        btn_docs.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(btn_docs)

        layout.addStretch(1)

        footer = QLabel("Academic & Rehabilitative Research Prototype.\nDedicated to Patient Empowerment.")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color: {T('TEXT_MUTED')}; font-size: {S(11)}px; font-style: italic;")
        layout.addWidget(footer)

        self._add_animated_card(card, parent_layout)


    def showEvent(self, event):
        super().showEvent(event)
        # Staggered entrance
        delay = 0
        for container in self.cards:
            container.start_anim(delay)
            delay += 75

    def paintEvent(self, event):
        # Deep slate radial gradient #060B10 to #0F1E2E
        painter = QPainter(self)
        grad = QRadialGradient(self.width() / 2, self.height() / 2, self.width())
        grad.setColorAt(0, QColor(T("BG_PANEL")))
        grad.setColorAt(1, QColor(T("BG_DARK")))
        painter.fillRect(self.rect(), grad)

    def _apply_theme(self) -> None:
        pass # Colors are hardcoded/tokenized in styles and paintEvent
