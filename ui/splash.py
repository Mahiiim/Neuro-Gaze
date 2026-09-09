"""
ui/splash.py
-------------
Custom Animated Splash Screen for Neuro-Gaze
"""

import math
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPixmap, QPen, QBrush, QPainterPath
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGraphicsOpacityEffect

class GlowingLogo(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.pixmap = QPixmap("assets/logo.jpg")
        # Ensure smooth scaling for logo
        self.pixmap = self.pixmap.scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self._glow_radius = 0
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._update_glow)
        self._glow_timer.start(50)
        self._time = 0.0

    def _update_glow(self):
        self._time += 0.1
        # Pulsate between Cyan (#00D2FF) and Neon Teal (#00F5D4)
        # We can just simulate it by varying alpha and radius
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx, cy = self.width() / 2, self.height() / 2
        
        # Draw pulsing glow
        glow_size = 170 + math.sin(self._time) * 10
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(5):
            alpha = int(40 - i * 8 + math.sin(self._time) * 10)
            if alpha < 0: alpha = 0
            
            # Mix Cyan and Teal
            r, g, b = 0, 220 + int(math.sin(self._time)*15), 255 - int(math.sin(self._time)*30)
            painter.setBrush(QColor(r, g, b, alpha))
            painter.drawEllipse(QPointF(cx, cy), glow_size/2 - i*2, glow_size/2 - i*2)
            
        # Draw Reticle / HUD target corners
        painter.setPen(QPen(QColor(0, 210, 255, 200), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        r_size = 180
        rc = r_size / 2
        
        # Top Left
        painter.drawLine(cx - rc, cy - rc, cx - rc + 15, cy - rc)
        painter.drawLine(cx - rc, cy - rc, cx - rc, cy - rc + 15)
        # Top Right
        painter.drawLine(cx + rc, cy - rc, cx + rc - 15, cy - rc)
        painter.drawLine(cx + rc, cy - rc, cx + rc, cy - rc + 15)
        # Bottom Left
        painter.drawLine(cx - rc, cy + rc, cx - rc + 15, cy + rc)
        painter.drawLine(cx - rc, cy + rc, cx - rc, cy + rc - 15)
        # Bottom Right
        painter.drawLine(cx + rc, cy + rc, cx + rc - 15, cy + rc)
        painter.drawLine(cx + rc, cy + rc, cx + rc, cy + rc - 15)

        # Draw actual logo
        path = QPainterPath()
        path.addEllipse(QPointF(cx, cy), 80, 80)
        painter.setClipPath(path)
        painter.drawPixmap(int(cx - 80), int(cy - 80), self.pixmap)

class AnimatedSplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(500, 400)
        
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.setSpacing(20)
        
        # Container for background
        self.bg_frame = QWidget(self)
        self.bg_frame.setFixedSize(500, 400)
        self.bg_frame.setStyleSheet("background-color: #0A1118; border-radius: 20px; border: 1px solid #1A2530;")
        
        # Wrap everything in bg_frame
        bg_layout = QVBoxLayout(self.bg_frame)
        bg_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.logo = GlowingLogo()
        bg_layout.addWidget(self.logo, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("color: #00D2FF; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; font-weight: bold; letter-spacing: 1px;")
        bg_layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(300, 4)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1A2530;
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #00F5D4;
                border-radius: 2px;
            }
        """)
        bg_layout.addWidget(self.progress_bar, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.layout.addWidget(self.bg_frame)
        
        # Opacity Effect for Fade In/Out
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)
        
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(600)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.scale_anim = QPropertyAnimation(self.logo, b"geometry")
        self.scale_anim.setDuration(600)
        self.scale_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
    def showEvent(self, event):
        super().showEvent(event)
        
        # Setup scale animation (simulate scale by animating geometry slightly)
        orig_rect = self.logo.geometry()
        shrunk_rect = orig_rect.adjusted(20, 20, -20, -20)
        
        self.scale_anim.setStartValue(shrunk_rect)
        self.scale_anim.setEndValue(orig_rect)
        
        self.fade_anim.start()
        self.scale_anim.start()

    def update_progress(self, message: str, value: int):
        self.status_label.setText(message)
        self.progress_bar.setValue(value)
        
    def fade_out(self, on_finished_callback):
        self.fade_anim.stop()
        self.fade_anim.setDuration(400)
        self.fade_anim.setStartValue(self.opacity_effect.opacity())
        self.fade_anim.setEndValue(0)
        self.fade_anim.finished.connect(on_finished_callback)
        self.fade_anim.start()
