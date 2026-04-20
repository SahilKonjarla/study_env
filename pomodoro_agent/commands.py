import os
import pwd
import subprocess
import sys
from typing import List

from .config import logger


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
