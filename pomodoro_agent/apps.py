from typing import List

from .commands import run_command, run_user_command
from .config import BLOCKED_APPS, REOPEN_APPS, logger


def app_is_running(app_name: str) -> bool:
    result = run_command(["pgrep", "-x", app_name])
    return result.returncode == 0


def kill_blocked_apps() -> List[str]:
    closed_apps: List[str] = []
    for app_name in BLOCKED_APPS:
        if not app_is_running(app_name):
            logger.debug("%s not running", app_name)
            continue

        result = run_command(["pkill", "-x", app_name])
        if result.returncode == 0:
            logger.info("closed blocked app: %s", app_name)
            closed_apps.append(app_name)
        else:
            logger.warning("failed to close blocked app %s: %s", app_name, result.stderr.strip())

    return closed_apps


def reopen_apps() -> List[str]:
    reopened_apps: List[str] = []
    for app_name in REOPEN_APPS:
        result = run_user_command(["open", "-a", app_name])
        if result.returncode == 0:
            logger.info("reopened app: %s", app_name)
            reopened_apps.append(app_name)
        else:
            logger.warning("failed to reopen app %s: %s", app_name, result.stderr.strip())
    return reopened_apps
