import logging
import os
import time
import subprocess
from typing import Optional
from ..system.exec import run_command

logger = logging.getLogger("pppoe_cred_helper.pppoe.server")

class PPPoEServer:
    """
    Manages the lifecycle of the pppoe-server process.
    """
    def __init__(self, interface: str, options_file: str):
        self.interface = interface
        self.options_file = options_file
        self.process: Optional[subprocess.Popen] = None

    def start(self, dry_run: bool = False):
        """Start the PPPoE server."""
        cmd = [
            "pppoe-server",
            "-C", "ftth",
            "-I", self.interface,
            "-N", "256",
            "-O", self.options_file
        ]
        
        if dry_run:
            logger.info("[DRY-RUN] Starting PPPoE server on %s", self.interface)
            return

        logger.info("Starting PPPoE server on %s", self.interface)
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=os.setpgrp # Create process group for clean killing
            )
            # Give it a moment to start
            time.sleep(1)
        except Exception as e:
            logger.error("Failed to start PPPoE server: %s", e)
            raise

    def stop(self, dry_run: bool = False):
        """Stop the PPPoE server."""
        if dry_run:
            logger.info("[DRY-RUN] Stopping PPPoE server")
            return

        if self.process and self.process.poll() is None:
            logger.info("Stopping PPPoE server (PID: %d)", self.process.pid)
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("PPPoE server didn't stop, killing...")
                self.process.kill()
        
        # Cleanup any stray pppoe-server processes just in case
        try:
            run_command(["pkill", "-f", "pppoe-server"], check=False, sudo=True)
        except Exception:
            pass
