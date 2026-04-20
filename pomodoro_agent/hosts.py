from typing import List

from .commands import require_sudo_for_hosts, run_command
from .config import BLOCKED_DOMAINS, HOSTS_PATH, MANAGED_END, MANAGED_START, logger


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

    logger.info(
        "hosts %s domain_count=%s",
        "blocked" if enable else "unblocked",
        len(BLOCKED_DOMAINS) if enable else 0,
    )
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
