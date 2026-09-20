"""
core/lifecycle.py
------------------
Centralized lifecycle management for UI modules. Ensures all dangling
QTimers, animations, audio synthesis nodes, and TTS speech calls are securely
halted when transitioning between major application views.
"""

from __future__ import annotations
from utils.logger import get_logger

log = get_logger(__name__)

class ActivityLifecycleManager:
    """Singleton manager for tracking and cleaning up resources."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
        
    def _init(self):
        self._timers = []
        self._anims = []
        self._hooks = []
        
    def register_timer(self, timer):
        """Register a QTimer. It will be stopped on cleanup."""
        if timer not in self._timers:
            self._timers.append(timer)
            
    def register_anim(self, anim):
        """Register a QAbstractAnimation. It will be stopped on cleanup."""
        if anim not in self._anims:
            self._anims.append(anim)
            
    def register_hook(self, func):
        """Register a callable to run on cleanup."""
        if func not in self._hooks:
            self._hooks.append(func)
            
    def stop_all(self, audio_synth=None, speech_engine=None):
        """Execute cleanup on all registered resources."""
        log.debug(f"ActivityLifecycleManager stopping {len(self._timers)} timers, {len(self._anims)} anims.")
        
        # 1. Stop Timers
        for t in self._timers:
            try:
                t.stop()
            except Exception:
                pass
        self._timers.clear()
        
        # 2. Stop Animations
        for a in self._anims:
            try:
                a.stop()
            except Exception:
                pass
        self._anims.clear()
        
        # 3. Custom Hooks
        for h in self._hooks:
            try:
                h()
            except Exception as e:
                log.warning(f"Lifecycle hook error: {e}")
        self._hooks.clear()
        
        # 4. Stop Speech Synthesis and Audio Voices
        if speech_engine:
            try:
                speech_engine.stop()
            except Exception:
                pass
                
        if audio_synth:
            try:
                audio_synth.stop_all_voices()
            except Exception:
                pass
