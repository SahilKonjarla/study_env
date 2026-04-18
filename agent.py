import atexit
import argparse
import json
import logging
import os
import pwd
import signal
import subprocess
import sys
import time
from typing import Dict, List, Optional
import urllib.error
import urllib.request


BACKEND_URL = os.environ.get("POMODORO_BACKEND_URL", "http://127.0.0.1:8000")
POLL_SECONDS = int(os.environ.get("POMODORO_POLL_SECONDS", "4"))
HOSTS_PATH = "/etc/hosts"
MANAGED_START = "# POMODORO_CONTROL_START"
MANAGED_END = "# POMODORO_CONTROL_END"
BLOCKED_DOMAINS = ("youtube.com", "www.youtube.com", "netflix.com", "www.netflix.com", "hulu.com", "www.hulu.com")
FOCUS_NAME = os.environ.get("POMODORO_FOCUS_NAME") or "Work"
FOCUS_ON_SHORTCUTS = (
    os.environ.get("POMODORO_FOCUS_ON_SHORTCUT") or "Pomodoro Work Focus On",
    os.environ.get("POMODORO_DND_ON_SHORTCUT") or "Pomodoro Focus On",
)
FOCUS_OFF_SHORTCUTS = (
    os.environ.get("POMODORO_FOCUS_OFF_SHORTCUT") or "Pomodoro Work Focus Off",
    os.environ.get("POMODORO_DND_OFF_SHORTCUT") or "Pomodoro Focus Off",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("pomodoro-agent")

last_mode: Optional[str] = None
restrictions_active = False
shutdown_cleanup_done = False


def run_command(command: List[str], check: bool = False) -> subprocess.CompletedProcess:
    logger.debug("running command: %s", " ".join(command))
    return subprocess.run(command, capture_output=True, check=check, text=True)


def run_user_command(command: List[str]) -> subprocess.CompletedProcess:
    sudo_user = os.environ.get("SUDO_USER")
    if not sudo_user or sudo_user == "root":
        return run_command(command)

    user_info = pwd.getpwnam(sudo_user)
    user_command = ["launchctl", "asuser", str(user_info.pw_uid), "sudo", "-u", sudo_user, *command]
    return run_command(user_command)


def open_user_url(url: str) -> subprocess.CompletedProcess:
    return run_user_command(["open", url])


def require_sudo_for_hosts() -> None:
    if os.geteuid() != 0:
        logger.error("Run with sudo to allow safe /etc/hosts updates: sudo python3 agent.py")
        sys.exit(1)


def fetch_status() -> Optional[Dict[str, object]]:
    try:
        with urllib.request.urlopen(f"{BACKEND_URL}/status", timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("status fetch failed: %s", exc)
        return None


def send_heartbeat() -> None:
    payload = json.dumps({"name": os.uname().nodename}).encode("utf-8")
    request = urllib.request.Request(
        f"{BACKEND_URL}/agent/heartbeat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5):
            logger.debug("heartbeat sent")
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.warning("heartbeat failed: %s", exc)


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


def remove_managed_hosts_block(hosts_text: str) -> str:
    lines = hosts_text.splitlines()
    cleaned: List[str] = []
    inside_block = False

    for line in lines:
        if line.strip() == MANAGED_START:
            inside_block = True
            continue
        if line.strip() == MANAGED_END:
            inside_block = False
            continue
        if not inside_block:
            cleaned.append(line)

    return "\n".join(cleaned).rstrip() + "\n"


def write_hosts_block(enable: bool) -> None:
    require_sudo_for_hosts()

    with open(HOSTS_PATH, "r", encoding="utf-8") as hosts_file:
        current_hosts = hosts_file.read()

    next_hosts = remove_managed_hosts_block(current_hosts)
    if enable:
        block_lines = [MANAGED_START]
        block_lines.extend(f"127.0.0.1 {domain}" for domain in BLOCKED_DOMAINS)
        block_lines.append(MANAGED_END)
        next_hosts = next_hosts.rstrip() + "\n\n" + "\n".join(block_lines) + "\n"

    if next_hosts == current_hosts:
        logger.info("hosts already %s", "blocked" if enable else "clean")
        return

    with open(HOSTS_PATH, "w", encoding="utf-8") as hosts_file:
        hosts_file.write(next_hosts)

    logger.info("hosts %s", "blocked" if enable else "unblocked")
    flush_dns_cache()


def flush_dns_cache() -> None:
    commands = [
        ["dscacheutil", "-flushcache"],
        ["killall", "-HUP", "mDNSResponder"],
    ]
    for command in commands:
        result = run_command(command)
        if result.returncode != 0:
            logger.debug("dns cache command failed for %s: %s", command[0], result.stderr.strip())
    logger.info("dns cache flush attempted")


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


def kill_discord() -> None:
    result = run_command(["pkill", "-x", "Discord"])
    if result.returncode == 0:
        logger.info("discord killed")
    else:
        logger.info("discord not running")


def apply_focus() -> None:
    global restrictions_active
    enable_focus()
    kill_discord()
    write_hosts_block(enable=True)
    restrictions_active = True


def cleanup_restrictions() -> None:
    global restrictions_active
    disable_focus()
    write_hosts_block(enable=False)
    restrictions_active = False


def handle_shutdown(signum: Optional[int] = None, frame: object = None) -> None:
    global shutdown_cleanup_done
    if shutdown_cleanup_done:
        if signum is not None:
            sys.exit(0)
        return
    shutdown_cleanup_done = True
    logger.info("shutdown cleanup")
    cleanup_restrictions()
    if signum is not None:
        sys.exit(0)


def enforce_mode(mode: str) -> None:
    if mode == "focus":
        logger.info("entering focus mode")
        apply_focus()
    else:
        logger.info("entering %s mode; removing restrictions", mode)
        cleanup_restrictions()


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


def main() -> None:
    global last_mode

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

    atexit.register(handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    logger.info("polling %s every %s seconds", BACKEND_URL, POLL_SECONDS)
    log_shortcuts_status()
    startup_status = fetch_status()
    if startup_status is None or startup_status.get("mode") != "focus":
        cleanup_restrictions()

    while True:
        status = fetch_status()
        if status is None:
            time.sleep(POLL_SECONDS)
            continue

        send_heartbeat()
        mode = str(status.get("mode", "idle"))
        if mode != last_mode:
            enforce_mode(mode)
            last_mode = mode

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
