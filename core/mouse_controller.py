"""
core/mouse_controller.py
-------------------------
Handles all system mouse interactions: smoothing, movement, and clicking.

Keeps PyAutoGUI calls in one place so the rest of the codebase never
imports pyautogui directly.
"""

from __future__ import annotations

import time

import numpy as np
import pyautogui

from utils.logger import get_logger

log = get_logger(__name__)

# Disable PyAutoGUI failsafe and inter-call pauses for real-time tracking
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0


class MouseController:
    """
    Converts normalised nose coordinates → smoothed screen coordinates
    and issues PyAutoGUI click events with a cooldown guard.
    """

    def __init__(
        self,
        alpha_min: float = 0.05,
        alpha_max: float = 0.25,
        click_cooldown: float = 1.0,
        range_x: tuple[float, float] = (0.38, 0.62),
        range_y: tuple[float, float] = (0.38, 0.62),
        sensitivity_x: float = 1.0,
        sensitivity_y: float = 1.0,
        fatigue_mode: bool = False,
    ) -> None:
        self.alpha_min = alpha_min
        self.alpha_max = alpha_max
        self.click_cooldown = click_cooldown
        self.range_x = list(range_x)
        self.range_y = list(range_y)
        self.sensitivity_x = sensitivity_x
        self.sensitivity_y = sensitivity_y
        self.fatigue_mode = fatigue_mode

        self._screen_w, self._screen_h = pyautogui.size()
        self._last_x: float | None = None
        self._last_y: float | None = None
        self._last_click_time: float = 0.0
        self._enabled: bool = True

    # ── public API ──────────────────────────────────────────────

    def update_config(
        self,
        alpha_min: float | None = None,
        alpha_max: float | None = None,
        click_cooldown: float | None = None,
        range_x: tuple[float, float] | None = None,
        range_y: tuple[float, float] | None = None,
        sensitivity_x: float | None = None,
        sensitivity_y: float | None = None,
        fatigue_mode: bool | None = None,
    ) -> None:
        """Hot-update configuration without restarting the tracker."""
        if alpha_min is not None:
            self.alpha_min = alpha_min
        if alpha_max is not None:
            self.alpha_max = alpha_max
        if click_cooldown is not None:
            self.click_cooldown = click_cooldown
        if range_x is not None:
            self.range_x = list(range_x)
        if range_y is not None:
            self.range_y = list(range_y)
        if sensitivity_x is not None:
            self.sensitivity_x = sensitivity_x
        if sensitivity_y is not None:
            self.sensitivity_y = sensitivity_y
        if fatigue_mode is not None:
            self.fatigue_mode = fatigue_mode

    def enable(self) -> None:
        """Allow mouse movement and clicks."""
        self._enabled = True
        log.info("Mouse controller enabled")

    def disable(self) -> None:
        """Block all mouse movement and clicks (emergency stop)."""
        self._enabled = False
        self._last_x = None
        self._last_y = None
        log.info("Mouse controller disabled")

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def process_nose(self, nose_x: float, nose_y: float) -> tuple[int, int]:
        """
        Map a normalised nose position to screen coordinates, apply smoothing,
        and move the mouse. Returns the final (screen_x, screen_y).
        """
        if not self._enabled:
            return pyautogui.position()

        # Map normalised nose range → screen dimensions
        tx = float(np.interp(nose_x, self.range_x, (0, self._screen_w)))
        ty = float(np.interp(nose_y, self.range_y, (0, self._screen_h)))

        # Apply sensitivity scaling around the screen centre
        cx, cy = self._screen_w / 2, self._screen_h / 2
        tx = cx + (tx - cx) * self.sensitivity_x
        ty = cy + (ty - cy) * self.sensitivity_y

        # Dynamic exponential smoothing
        sx = self._smooth(tx, self._last_x)
        sy = self._smooth(ty, self._last_y)
        self._last_x, self._last_y = sx, sy

        # Clamp to screen bounds
        final_x = int(np.clip(sx, 0, self._screen_w - 1))
        final_y = int(np.clip(sy, 0, self._screen_h - 1))

        pyautogui.moveTo(final_x, final_y, _pause=False)
        return final_x, final_y

    def try_click(self) -> bool:
        """
        Issue a left-click if the cooldown has elapsed.
        Returns True if a click was issued.
        """
        if not self._enabled:
            return False
        now = time.time()
        if (now - self._last_click_time) >= self.click_cooldown:
            self._last_click_time = now
            try:
                pyautogui.click()
                log.debug("Click issued")
            except Exception as exc:
                log.warning("PyAutoGUI click failed: %s", exc)
            return True
        return False

    def reset_position(self) -> None:
        """Clear the smoothing state (e.g. after re-enabling tracking)."""
        self._last_x = None
        self._last_y = None

    # ── private ─────────────────────────────────────────────────

    def _smooth(self, target: float, last: float | None) -> float:
        """
        Dynamic exponential smoothing.

        Alpha scales with the distance between target and last position:
        fast movements get higher alpha (less lag) while tiny jitters get
        lower alpha (more dampening).
        """
        if last is None:
            return target
        dist = abs(target - last)
        alpha = float(np.clip(dist * 2.0, self.alpha_min, self.alpha_max))
        
        if self.fatigue_mode:
            alpha *= 0.5  # Halve the alpha to heavily increase smoothing
            
        return last + alpha * (target - last)
