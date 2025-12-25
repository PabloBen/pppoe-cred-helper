import logging
import subprocess
from typing import List, Optional, Union

logger = logging.getLogger("pppoe_cred_helper.system.exec")

class CommandError(Exception):
    """Custom exception for command failures."""
    def __init__(self, cmd: List[str], returncode: int, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command '{' '.join(cmd)}' failed with exit code {returncode}: {stderr}")

def run_command(
    cmd: List[str],
    check: bool = True,
    capture: bool = False,
    dry_run: bool = False,
    sudo: bool = False
) -> subprocess.CompletedProcess:
    """
    Wrapper around subprocess.run with logging and dry-run support.
    """
    if sudo:
        cmd = ["sudo"] + cmd

    cmd_str = " ".join(cmd)
    
    if dry_run:
        logger.info("[DRY-RUN] %s", cmd_str)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    logger.debug("Executing: %s", cmd_str)
    try:
        result = subprocess.run(
            cmd,
            check=check,
            text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error("Command failed: %s (exit code %d)", cmd_str, e.returncode)
        if e.stderr:
            logger.error("Stderr: %s", e.stderr.strip())
        raise CommandError(cmd, e.returncode, e.stderr or "") from e
