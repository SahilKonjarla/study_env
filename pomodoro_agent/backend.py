import json
import os
from typing import Dict, List, Optional
import urllib.error
import urllib.request

from .config import BACKEND_URL, logger


def fetch_status() -> Optional[Dict[str, object]]:
    try:
        with urllib.request.urlopen(f"{BACKEND_URL}/status", timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("status fetch failed: %s", exc)
        return None


def request_backend_reset(reason: str) -> None:
    logger.info("requesting backend reset: %s", reason)
    try:
        with urllib.request.urlopen(f"{BACKEND_URL}/reset", timeout=5) as response:
            logger.info("backend reset response status=%s", response.status)
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("backend reset failed: %s", exc)


def send_heartbeat(closed_apps: Optional[List[str]] = None, reopened_apps: Optional[List[str]] = None) -> None:
    payload = json.dumps(
        {
            "name": os.uname().nodename,
            "closed_apps": closed_apps or [],
            "reopened_apps": reopened_apps or [],
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{BACKEND_URL}/agent/heartbeat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5):
            logger.debug(
                "heartbeat sent closed_apps=%s reopened_apps=%s",
                closed_apps or [],
                reopened_apps or [],
            )
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("heartbeat failed: %s", exc)
