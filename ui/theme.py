"""
ui/theme.py
-----------
Unified design-system theme module for Neuro-Gaze.

Centralises all colour tokens so that future palette changes happen in one
place.  Provides Dark, Light, and High-Contrast themes — switchable at
runtime without restart.

Clinical rationale
------------------
Patients' visual sensitivity varies widely:
  • Some need low-glare light backgrounds (daytime, well-lit rooms).
  • Others need dark backgrounds to reduce eye strain in dim rooms.
  • High-contrast (black/yellow, WCAG-AAA) is essential for patients with
    visual-field or contrast-sensitivity impairments.
Dark/Light/High-Contrast switching is therefore a clinical usability
feature, not just cosmetic.

Usage
-----
    from ui.theme import T, theme_manager, set_theme, hex_to_rgba

    # Read a token
    color = T("ACCENT")

    # Switch theme (emits theme_changed signal)
    set_theme("light")

    # Connect a widget refresh to theme changes
    theme_manager().theme_changed.connect(self._apply_theme)
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from utils.logger import get_logger

log = get_logger(__name__)


# ── Dark theme (default) ────────────────────────────────────────
# Deep navy base with bright cyan accent — premium, low-glare for dim rooms.

DARK_THEME: dict[str, str] = {
    # Backgrounds
    "BG_DARK":          "#0A1118",
    "BG_PANEL":         "#101F30",
    "BG_CARD":          "#1c2128",
    "BG_SIDEBAR":       "#0A1118",
    "BG_KEY":           "#21262d",
    "BG_KEY_SPECIAL":   "#1f3045",
    "BG_KEY_DANGER":    "#3d1f1f",
    "BG_KEY_SUCCESS":   "#1f3d1f",
    "BG_PHRASE_BTN":    "#1a2d42",
    # Accent
    "ACCENT":           "#00D2FF",
    "ACCENT_HOVER":     "#00F5D4",
    "ACCENT_PRESSED":   "#0090cc",
    # Text
    "TEXT_PRIMARY":     "#FFFFFF",
    "TEXT_MUTED":       "#A0B2C6",
    # Borders
    "BORDER":          "rgba(255, 255, 255, 0.1)",
    "BORDER_SOLID":    "#30363d",
    # Semantic colours
    "SUCCESS":         "#2ED573",
    "WARNING":         "#FFA502",
    "DANGER":          "#FF4757",
    # Derived / widget-specific
    "NAV_BTN_BG":      "rgba(255, 255, 255, 0.05)",
    "NAV_ACTIVE_BG":   "rgba(0, 210, 255, 0.15)",
    "KEY_HOVER_TEXT":  "#0d1117",
    "PHRASE_BORDER":   "#264a6e",
    "STOP_BTN_BG":     "#E63946",
    "ALERT_BG":        "#FF0000",
    "ALERT_BORDER":    "#AA0000",
    "ALERT_HOVER":     "#FF3333",
    "EMERGENCY_HOVER": "#ff6b6b",
    "APPLY_HOVER":     "#33c6ff",
}


# ── Light theme ─────────────────────────────────────────────────
# Soft off-white base (NOT pure #FFF — reduces glare for patients who
# stare at the screen for extended periods).  Accent blue is darkened
# to maintain WCAG-AA contrast on light backgrounds.

LIGHT_THEME: dict[str, str] = {
    "BG_DARK":          "#F0F2F5",
    "BG_PANEL":         "#FFFFFF",
    "BG_CARD":          "#F5F7FA",
    "BG_SIDEBAR":       "#E8ECF1",
    "BG_KEY":           "#E2E6EB",
    "BG_KEY_SPECIAL":   "#D0E0F0",
    "BG_KEY_DANGER":    "#FDE8E8",
    "BG_KEY_SUCCESS":   "#E8FDE8",
    "BG_PHRASE_BTN":    "#DDE8F0",
    "ACCENT":           "#0077B6",
    "ACCENT_HOVER":     "#00A896",
    "ACCENT_PRESSED":   "#005A8C",
    "TEXT_PRIMARY":     "#1A1A2E",
    "TEXT_MUTED":       "#5A6577",
    "BORDER":          "rgba(0, 0, 0, 0.12)",
    "BORDER_SOLID":    "#D0D7DE",
    "SUCCESS":         "#1B8A3E",
    "WARNING":         "#BF6A00",
    "DANGER":          "#CF222E",
    "NAV_BTN_BG":      "rgba(0, 0, 0, 0.04)",
    "NAV_ACTIVE_BG":   "rgba(0, 119, 182, 0.12)",
    "KEY_HOVER_TEXT":  "#FFFFFF",
    "PHRASE_BORDER":   "#A0C0D8",
    "STOP_BTN_BG":     "#CF222E",
    "ALERT_BG":        "#CF222E",
    "ALERT_BORDER":    "#A01020",
    "ALERT_HOVER":     "#E54B4B",
    "EMERGENCY_HOVER": "#E54B4B",
    "APPLY_HOVER":     "#339ED6",
}


# ── High-contrast theme ─────────────────────────────────────────
# Black/yellow WCAG-AAA palette for patients with visual-field or
# contrast-sensitivity issues.  Every token is chosen for maximum
# foreground-background contrast.

HIGH_CONTRAST_THEME: dict[str, str] = {
    "BG_DARK":          "#000000",
    "BG_PANEL":         "#0A0A0A",
    "BG_CARD":          "#1A1A1A",
    "BG_SIDEBAR":       "#000000",
    "BG_KEY":           "#1A1A1A",
    "BG_KEY_SPECIAL":   "#2A2A00",
    "BG_KEY_DANGER":    "#3A0000",
    "BG_KEY_SUCCESS":   "#003A00",
    "BG_PHRASE_BTN":    "#1A1A00",
    "ACCENT":           "#FFD700",
    "ACCENT_HOVER":     "#FFEA00",
    "ACCENT_PRESSED":   "#CCA800",
    "TEXT_PRIMARY":     "#FFFFFF",
    "TEXT_MUTED":       "#E0E0E0",
    "BORDER":          "rgba(255, 215, 0, 0.4)",
    "BORDER_SOLID":    "#FFD700",
    "SUCCESS":         "#00FF00",
    "WARNING":         "#FFAA00",
    "DANGER":          "#FF0000",
    "NAV_BTN_BG":      "rgba(255, 255, 255, 0.08)",
    "NAV_ACTIVE_BG":   "rgba(255, 215, 0, 0.2)",
    "KEY_HOVER_TEXT":  "#000000",
    "PHRASE_BORDER":   "#FFD700",
    "STOP_BTN_BG":     "#FF0000",
    "ALERT_BG":        "#FF0000",
    "ALERT_BORDER":    "#CC0000",
    "ALERT_HOVER":     "#FF4444",
    "EMERGENCY_HOVER": "#FF4444",
    "APPLY_HOVER":     "#FFE44D",
}


_THEMES: dict[str, dict[str, str]] = {
    "dark": DARK_THEME,
    "light": LIGHT_THEME,
    "high_contrast": HIGH_CONTRAST_THEME,
}


# ── Accessibility Scaling ───────────────────────────────────────

UI_SCALE_FACTORS = {
    "small": 0.85,
    "medium": 1.0,
    "large": 1.25,
    "extra_large": 1.5,
}


# ── ThemeManager singleton ──────────────────────────────────────

class ThemeManager(QObject):
    """
    Singleton that holds the active colour palette and emits
    ``theme_changed`` whenever the user switches themes.

    Every widget that renders themed styles should:
      1. Connect ``theme_manager().theme_changed`` to its refresh method.
      2. Call ``T("TOKEN_NAME")`` inside that method to read current values.
    """

    theme_changed = Signal()

    _instance: ThemeManager | None = None

    @classmethod
    def instance(cls) -> ThemeManager:
        """Return (or create) the global ThemeManager singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        super().__init__()
        self._current: dict[str, str] = dict(DARK_THEME)
        self._theme_name: str = "dark"
        self._scale_factor: float = 1.0
        self._scale_name: str = "medium"

    # ── public API ──────────────────────────────────────────────

    def set_theme(self, name: str) -> None:
        """Switch the active palette by name and notify all listeners."""
        palette = _THEMES.get(name)
        if palette is None:
            log.warning("Unknown theme %r — falling back to dark", name)
            palette = DARK_THEME
            name = "dark"
        self._current = dict(palette)
        self._theme_name = name
        log.info("Theme switched to: %s", name)
        self.theme_changed.emit()

    def set_scale(self, name: str) -> None:
        """Switch the active UI scale by name and notify all listeners."""
        factor = UI_SCALE_FACTORS.get(name)
        if factor is None:
            log.warning("Unknown scale %r — falling back to medium", name)
            factor = 1.0
            name = "medium"
        self._scale_factor = factor
        self._scale_name = name
        log.info("Scale switched to: %s", name)
        self.theme_changed.emit()

    def get(self, key: str) -> str:
        """Return the current value of colour token *key*."""
        val = self._current.get(key)
        if val is None:
            log.warning("Missing theme token: %r", key)
            return "#FF00FF"  # magenta = clearly visible "missing" marker
        return val

    @property
    def name(self) -> str:
        """Name of the currently active theme."""
        return self._theme_name

    def scale(self, value: int | float) -> int:
        """Scale a pixel value by the active UI scale factor."""
        return int(round(value * self._scale_factor))


# ── Module-level convenience functions ──────────────────────────

def T(key: str) -> str:
    """Shorthand: read a colour token from the active theme."""
    return ThemeManager.instance().get(key)


def S(value: int | float) -> int:
    """Shorthand: scale a pixel value using the active UI scale factor."""
    return ThemeManager.instance().scale(value)


def set_theme(name: str) -> None:
    """Switch the global theme by name ('dark', 'light', 'high_contrast')."""
    ThemeManager.instance().set_theme(name)


def set_scale(name: str) -> None:
    """Switch the global UI scale ('small', 'medium', 'large', 'extra_large')."""
    ThemeManager.instance().set_scale(name)


def theme_manager() -> ThemeManager:
    """Return the singleton ThemeManager instance."""
    return ThemeManager.instance()


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """
    Convert a hex colour string to an ``rgba(R,G,B,alpha)`` CSS value.

    Examples
    --------
    >>> hex_to_rgba("#2ED573", 0.15)
    'rgba(46,213,115,0.15)'
    """
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return f"rgba(128,128,128,{alpha})"
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"
