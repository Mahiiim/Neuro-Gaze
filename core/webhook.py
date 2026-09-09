"""
core/webhook.py
---------------
Asynchronous Webhook Engine for Caregiver Notifications.
Sends payloads to endpoints like Discord, Slack, or generic webhooks
without blocking the Qt event loop.
"""

from __future__ import annotations

import json
import threading
import urllib.request
import urllib.error
from utils.logger import get_logger

log = get_logger(__name__)

class CaregiverNotifier:
    """Handles sending asynchronous webhooks to configured URLs."""
    
    @staticmethod
    def send_webhook(url: str, message: str, is_emergency: bool = False) -> None:
        """
        Send a JSON payload to the webhook URL on a background thread.
        """
        if not url or not url.strip() or not url.startswith("http"):
            log.warning("Invalid webhook URL configured. Skipping notification.")
            return

        def _post_request():
            log.info("Sending %s webhook...", "EMERGENCY" if is_emergency else "PING")
            payload = {
                "content": message,
                # Discord/Slack compatible fields
                "username": "Neuro-Gaze Alert",
                "avatar_url": "https://raw.githubusercontent.com/google/material-design-icons/master/png/alert/error/materialicons/48dp/2x/baseline_error_black_48dp.png" if is_emergency else "https://raw.githubusercontent.com/google/material-design-icons/master/png/social/notifications/materialicons/48dp/2x/baseline_notifications_black_48dp.png"
            }
            
            # Optional embed for Discord for a richer appearance
            if is_emergency:
                payload["embeds"] = [{
                    "title": "🚨 PATIENT EMERGENCY 🚨",
                    "description": message,
                    "color": 16711680 # Red
                }]

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url.strip(), data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("User-Agent", "Neuro-Gaze/2.0")

            try:
                with urllib.request.urlopen(req, timeout=1.5) as response:
                    status = response.getcode()
                    if status in (200, 204):
                        log.info("Webhook successfully delivered.")
                    else:
                        log.warning(f"Webhook delivered but returned status {status}")
            except Exception:
                # Silently ignore all network errors (e.g. no internet on ESP32 hotspot)
                # to prevent the UI from freezing or lagging.
                pass

        # Fire and forget
        t = threading.Thread(target=_post_request, daemon=True)
        t.start()
