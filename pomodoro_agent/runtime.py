import argparse
import atexit
import signal
import sys
import time
from typing import List, Optional

from .apps import kill_blocked_apps, reopen_apps
from .backend import fetch_status, request_backend_reset, send_heartbeat
from .commands import open_user_url, require_sudo_for_hosts
from .config import POLL_SECONDS, log_runtime_config, logger
from .focus import disable_focus, enable_focus, log_shortcuts_status
from .hosts import write_hosts_block
from .timers import start_break_timer


last_mode: Optional[str] = None
restrictions_active = False
shutdown_cleanup_done = False


def apply_focus() -> List[str]:
    global restrictions_active
    enable_focus()
    closed_apps = kill_blocked_apps()
    write_hosts_block(enable=True)
    restrictions_active = True
    return closed_apps


def enforce_focus_poll() -> List[str]:
    return kill_blocked_apps()


def cleanup_restrictions(reopen_blocked_apps: bool = False) -> List[str]:
    global restrictions_active
    was_active = restrictions_active
    logger.info(
        "cleanup starting restrictions_active=%s reopen_blocked_apps=%s",
        restrictions_active,
        reopen_blocked_apps,
    )
    disable_focus()
    write_hosts_block(enable=False)
    restrictions_active = False
    if reopen_blocked_apps and was_active:
        reopened_apps = reopen_apps()
        logger.info("cleanup complete reopened_apps=%s", reopened_apps)
        return reopened_apps
    logger.info("cleanup complete reopened_apps=[]")
    return []


def shutdown_cleanup(reason: str, reset_backend: bool = True, reopen_blocked_apps: bool = True) -> None:
    global shutdown_cleanup_done
    if shutdown_cleanup_done:
        return
    shutdown_cleanup_done = True
    logger.info("shutdown cleanup starting reason=%s", reason)
    if reset_backend:
        request_backend_reset(reason)
    reopened_apps = cleanup_restrictions(reopen_blocked_apps=reopen_blocked_apps)
    if reopened_apps:
        send_heartbeat(reopened_apps=reopened_apps)
    logger.info("shutdown cleanup finished reason=%s", reason)


def handle_shutdown(signum: Optional[int] = None, frame: object = None) -> None:
    reason = f"signal {signum}" if signum is not None else "process exit"
    shutdown_cleanup(reason=reason, reset_backend=True, reopen_blocked_apps=True)
    if signum is not None:
        sys.exit(0)


def enforce_mode(mode: str, remaining_time: object = None, previous_mode: Optional[str] = None) -> List[str]:
    if mode == "break" and previous_mode != "paused":
        try:
            start_break_timer(int(remaining_time or 0))
        except Exception:
            logger.exception("failed to start Apple break timer")

    if mode == "focus":
        logger.info("entering focus mode")
        return apply_focus()

    logger.info("entering %s mode; removing restrictions", mode)
    reopened_apps = cleanup_restrictions(reopen_blocked_apps=True)
    if reopened_apps:
        send_heartbeat(reopened_apps=reopened_apps)
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pomodoro macOS enforcement agent")
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="remove restrictions and exit without polling the backend",
    )
    parser.add_argument(
        "--check-shortcuts",
        action="store_true",
        help="verify the Focus Shortcuts used for macOS Focus and exit",
    )
    parser.add_argument(
        "--open-shortcuts",
        action="store_true",
        help="open the Shortcuts app and Focus settings, then exit",
    )
    return parser.parse_args()


def register_shutdown_handlers() -> None:
    atexit.register(handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, handle_shutdown)
    if hasattr(signal, "SIGQUIT"):
        signal.signal(signal.SIGQUIT, handle_shutdown)


def poll_loop() -> None:
    global last_mode

    while True:
        status = fetch_status()
        if status is None:
            logger.info("backend status unavailable; retrying in %s seconds", POLL_SECONDS)
            time.sleep(POLL_SECONDS)
            continue

        mode = str(status.get("mode", "idle"))
        remaining_time = status.get("remaining_time")
        closed_apps: List[str] = []
        if mode != last_mode:
            logger.info("mode change detected previous=%s current=%s remaining_time=%s", last_mode, mode, remaining_time)
            previous_mode = last_mode
            closed_apps = enforce_mode(mode, remaining_time=remaining_time, previous_mode=previous_mode)
            last_mode = mode
        elif mode == "focus":
            closed_apps = enforce_focus_poll()

        if closed_apps:
            logger.info("focus poll closed_apps=%s", closed_apps)
        send_heartbeat(closed_apps=closed_apps)

        time.sleep(POLL_SECONDS)


def main() -> None:
    args = parse_args()

    if args.open_shortcuts:
        open_user_url("shortcuts://")
        open_user_url("x-apple.systempreferences:com.apple.preference.notifications")
        return

    if args.check_shortcuts:
        if log_shortcuts_status():
            return
        sys.exit(1)

    require_sudo_for_hosts()

    if args.cleanup:
        logger.info("cleanup-only mode")
        cleanup_restrictions()
        return

    register_shutdown_handlers()
    log_runtime_config()
    logger.info("starting poll loop")
    log_shortcuts_status()

    startup_status = fetch_status()
    if startup_status is None or startup_status.get("mode") != "focus":
        logger.info("startup status is not focus; ensuring local restrictions are clean")
        cleanup_restrictions()

    try:
        poll_loop()
    except SystemExit:
        raise
    except Exception:
        logger.exception("agent poll loop crashed; resetting backend and cleaning up")
        shutdown_cleanup(reason="poll loop exception", reset_backend=True, reopen_blocked_apps=True)
        sys.exit(1)
