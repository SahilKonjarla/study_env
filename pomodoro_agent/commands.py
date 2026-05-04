import os
import pwd
import subprocess
import sys
from typing import List, Optional

from .config import logger


def run_command(command: List[str], check: bool = False, input_text: Optional[str] = None) -> subprocess.CompletedProcess:
    logger.debug("running command: %s", " ".join(command))
    return subprocess.run(command, capture_output=True, check=check, input=input_text, text=True)


def run_user_command(command: List[str], input_text: Optional[str] = None) -> subprocess.CompletedProcess:
    sudo_user = os.environ.get("SUDO_USER")
    if not sudo_user or sudo_user == "root":
        return run_command(command, input_text=input_text)

    user_info = pwd.getpwnam(sudo_user)
    user_command = ["launchctl", "asuser", str(user_info.pw_uid), "sudo", "-u", sudo_user, *command]
    return run_command(user_command, input_text=input_text)


def open_user_url(url: str) -> subprocess.CompletedProcess:
    return run_user_command(["open", url])


def require_sudo_for_hosts() -> None:
    if os.geteuid() != 0:
        logger.error("Run with sudo to allow safe /etc/hosts updates: sudo python3 agent.py")
        sys.exit(1)
