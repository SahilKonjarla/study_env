from .commands import run_user_command
from .config import BREAK_TIMER_SHORTCUT, logger


def start_break_timer(seconds: int) -> None:
    duration_seconds = max(1, int(seconds or 0))
    shortcut_input = f"{duration_seconds} seconds"
    result = run_user_command(["shortcuts", "run", BREAK_TIMER_SHORTCUT, "-i", shortcut_input])
    if result.returncode == 0:
        logger.info(
            "Apple break timer started via shortcut=%r duration_seconds=%s",
            BREAK_TIMER_SHORTCUT,
            duration_seconds,
        )
        return

    logger.warning(
        "Apple break timer shortcut failed shortcut=%r duration_seconds=%s",
        BREAK_TIMER_SHORTCUT,
        duration_seconds,
    )
    if result.stderr.strip():
        logger.warning("Apple break timer stderr: %s", result.stderr.strip())
