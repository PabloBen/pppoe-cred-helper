import logging
import subprocess
from typing import Optional, Iterator
from ..system.exec import CommandError

logger = logging.getLogger("pppoe_cred_helper.capture.tshark")

class TSharkCapture:
    """
    Handles capturing PPPoE/PAP traffic using tshark.
    Returns a stream of relevant output lines.
    """
    def __init__(self, interface: str):
        self.interface = interface
        self.process: Optional[subprocess.Popen] = None

    def start(self, dry_run: bool = False) -> Iterator[str]:
        """
        Start tshark and yield lines of output.
        Uses -T fields to get structured data if possible, or -T text for PAP.
        """
        # We look for PAP Authenticate-Request
        # Format: PAP: Authenticate-Request (Peer-ID='...', Password='...')
        cmd = [
            "tshark",
            "-i", self.interface,
            "-n",      # Don't resolve names
            "-l",      # Line buffered
            "-T", "text",
            "-Y", "ppp.protocol == 0xc023" # Filtering for PAP
        ]

        if dry_run:
            logger.info("[DRY-RUN] Starting tshark on %s", self.interface)
            return iter([])

        logger.info("Starting tshark on %s", self.interface)
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            print(f"{cmd}")
            # Fail fast if tshark bails immediately (bad iface, perms, etc.)
            if self.process.poll() is not None:
                err = ""
                if self.process.stderr:
                    err = self.process.stderr.read().strip()
                raise CommandError(cmd, self.process.returncode or 1, err)
            return self.process.stdout
        except Exception as e:
            logger.error("Failed to start tshark: %s", e)
            raise

    def stop(self, dry_run: bool = False):
        """Stop the tshark process."""
        if dry_run:
            return

        if self.process and self.process.poll() is None:
            logger.info("Stopping tshark (PID: %d)", self.process.pid)
            self.process.terminate()
            try:
                self.process.wait(timeout=3000)
            except subprocess.TimeoutExpired:
                self.process.kill()
