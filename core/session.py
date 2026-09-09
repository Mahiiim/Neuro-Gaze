"""
core/session.py
---------------
Telemetry and session logger to persist usage patterns.
Writes to logs/session_history.json
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from utils.logger import get_logger

log = get_logger(__name__)

class SessionLogger:
    """Logs session start/end and critical events."""
    
    LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "session_history.json")

    def __init__(self):
        self._session_start = time.time()
        self._events = []
        
        # Ensure logs directory exists
        os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)

    def log_event(self, event_type: str, details: str = "") -> None:
        """Log a specific event (e.g. EMERGENCY, PING) during this session."""
        self._events.append({
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "details": details
        })
        log.debug(f"Session event logged: {event_type} - {details}")

    def end_session(self) -> None:
        """Write the session to disk on application close."""
        duration = time.time() - self._session_start
        
        session_data = {
            "start_time": datetime.fromtimestamp(self._session_start).isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "events": self._events
        }
        
        history = []
        if os.path.exists(self.LOG_FILE):
            try:
                with open(self.LOG_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception as e:
                log.warning(f"Could not read existing session history: {e}")

        history.append(session_data)
        
        try:
            with open(self.LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
            log.info(f"Session history saved to {self.LOG_FILE}")
        except Exception as e:
            log.error(f"Failed to write session history: {e}")

# Global singleton-like instance
session_logger = SessionLogger()
