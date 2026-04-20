from typing import List

from .commands import run_user_command
from .config import FOCUS_NAME, FOCUS_OFF_SHORTCUTS, FOCUS_ON_SHORTCUTS, logger


def list_shortcuts() -> List[str]:
    result = run_user_command(["shortcuts", "list"])
    if result.returncode != 0:
        logger.warning("could not list Shortcuts: %s", result.stderr.strip())
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def log_shortcuts_status() -> bool:
    shortcuts = set(list_shortcuts())
    on_found = next((name for name in FOCUS_ON_SHORTCUTS if name in shortcuts), None)
    off_found = next((name for name in FOCUS_OFF_SHORTCUTS if name in shortcuts), None)

    if on_found and off_found:
        logger.info("%s Focus shortcuts found: on=%r off=%r", FOCUS_NAME, on_found, off_found)
        return True

    logger.warning("missing Focus shortcuts")
    logger.warning("create shortcuts named %r and %r", FOCUS_ON_SHORTCUTS[0], FOCUS_OFF_SHORTCUTS[0])
    logger.warning("each shortcut should use Apple's Set Focus action for the %r Focus", FOCUS_NAME)
    logger.warning("override names with POMODORO_FOCUS_ON_SHORTCUT and POMODORO_FOCUS_OFF_SHORTCUT")
    return False


def enable_focus() -> None:
    shortcut_commands = [["shortcuts", "run", name] for name in FOCUS_ON_SHORTCUTS]
    for command in shortcut_commands:
        result = run_user_command(command)
        if result.returncode == 0:
            logger.info("%s Focus enabled via %s", FOCUS_NAME, " ".join(command))
            return
        logger.warning("Focus enable command failed: %s", " ".join(command))
        if result.stderr.strip():
            logger.warning("Focus enable stderr: %s", result.stderr.strip())
    logger.warning("could not enable %s Focus automatically; continuing", FOCUS_NAME)


def disable_focus() -> None:
    shortcut_commands = [["shortcuts", "run", name] for name in FOCUS_OFF_SHORTCUTS]
    for command in shortcut_commands:
        result = run_user_command(command)
        if result.returncode == 0:
            logger.info("%s Focus disabled via %s", FOCUS_NAME, " ".join(command))
            return
        logger.warning("Focus disable command failed: %s", " ".join(command))
        if result.stderr.strip():
            logger.warning("Focus disable stderr: %s", result.stderr.strip())
    logger.warning("could not disable %s Focus automatically; continuing cleanup", FOCUS_NAME)
