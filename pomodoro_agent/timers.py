import os
import tempfile

from .commands import run_user_command
from .config import BREAK_TIMER_SHORTCUT, logger


def start_break_timer(seconds: int) -> None:
    duration_seconds = max(1, int(seconds or 0))
    shortcut_input = f"{duration_seconds} seconds"
    input_path = ""
    try:
        with tempfile.NamedTemporaryFile("w", prefix="pomodoro-break-timer-", suffix=".txt", delete=False) as input_file:
            input_file.write(shortcut_input)
            input_path = input_file.name
        os.chmod(input_path, 0o644)

        result = run_user_command(["shortcuts", "run", BREAK_TIMER_SHORTCUT, "-i", input_path])
        if result.returncode == 0:
            logger.info(
                "Apple break timer started via shortcut=%r duration_seconds=%s",
                BREAK_TIMER_SHORTCUT,
                duration_seconds,
            )
            return
    finally:
        if input_path:
            try:
                os.unlink(input_path)
            except OSError:
                logger.debug("could not remove temporary shortcut input file path=%s", input_path)

    logger.warning(
        "Apple break timer shortcut failed shortcut=%r duration_seconds=%s",
        BREAK_TIMER_SHORTCUT,
        duration_seconds,
    )
    if result.stderr.strip():
        logger.warning("Apple break timer stderr: %s", result.stderr.strip())
