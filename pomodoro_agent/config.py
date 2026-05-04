import logging
import os


BACKEND_URL = os.environ.get("POMODORO_BACKEND_URL", "http://127.0.0.1:8000")
POLL_SECONDS = int(os.environ.get("POMODORO_POLL_SECONDS", "4"))
HOSTS_PATH = "/etc/hosts"
MANAGED_START = "# POMODORO_CONTROL_START"
MANAGED_END = "# POMODORO_CONTROL_END"

BLOCKED_DOMAINS = (
    "youtube.com",
    "www.youtube.com",
    "netflix.com",
    "www.netflix.com",
    "hulu.com",
    "www.hulu.com",
    "twitch.tv",
    "www.twitch.tv",
    "m.twitch.tv",
    "player.twitch.tv",
)

BLOCKED_APPS = tuple(
    app.strip()
    for app in os.environ.get("POMODORO_BLOCKED_APPS", "Discord,Messages,Mail").split(",")
    if app.strip()
)
REOPEN_APPS = tuple(
    app.strip()
    for app in os.environ.get("POMODORO_REOPEN_APPS", ",".join(BLOCKED_APPS)).split(",")
    if app.strip()
)

FOCUS_NAME = os.environ.get("POMODORO_FOCUS_NAME") or "Work"
FOCUS_ON_SHORTCUTS = (
    os.environ.get("POMODORO_FOCUS_ON_SHORTCUT") or "Pomodoro Work Focus On",
    os.environ.get("POMODORO_DND_ON_SHORTCUT") or "Pomodoro Focus On",
)
FOCUS_OFF_SHORTCUTS = (
    os.environ.get("POMODORO_FOCUS_OFF_SHORTCUT") or "Pomodoro Work Focus Off",
    os.environ.get("POMODORO_DND_OFF_SHORTCUT") or "Pomodoro Focus Off",
)
BREAK_TIMER_SHORTCUT = os.environ.get("POMODORO_BREAK_TIMER_SHORTCUT") or "Pomodoro Start Break Timer"


def configure_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return logging.getLogger("pomodoro-agent")


logger = configure_logging()


def log_runtime_config() -> None:
    logger.info("backend_url=%s poll_seconds=%s", BACKEND_URL, POLL_SECONDS)
    logger.info("blocked_domains=%s", ", ".join(BLOCKED_DOMAINS))
    logger.info("blocked_apps=%s", ", ".join(BLOCKED_APPS) or "(none)")
    logger.info("reopen_apps=%s", ", ".join(REOPEN_APPS) or "(none)")
    logger.info("focus_name=%s", FOCUS_NAME)
    logger.info("break_timer_shortcut=%s", BREAK_TIMER_SHORTCUT)
