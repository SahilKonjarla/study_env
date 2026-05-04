from .commands import run_user_command
from .config import BREAK_TIMER_SHORTCUT, logger


def start_break_timer(seconds: int) -> None:
    duration_seconds = max(1, int(seconds or 0))
    duration_minutes = max(1, round(duration_seconds / 60))
    result = run_user_command(
        ["shortcuts", "run", BREAK_TIMER_SHORTCUT, "-i", "-"],
        input_text=f"{duration_minutes}\n",
    )
    if result.returncode == 0:
        logger.info(
            "Apple break timer started via shortcut=%r duration_minutes=%s",
            BREAK_TIMER_SHORTCUT,
            duration_minutes,
        )
        return

    logger.warning(
        "Apple break timer shortcut failed shortcut=%r duration_minutes=%s",
        BREAK_TIMER_SHORTCUT,
        duration_minutes,
    )
    if result.stderr.strip():
        logger.warning("Apple break timer stderr: %s", result.stderr.strip())
