import logging
import os
import shutil
import sys
from typing import List, Tuple

logger = logging.getLogger("pppoe_cred_helper.system.capabilities")

REQUIRED_PACKAGES = {
    "tshark": "tshark",
    "pppoe-server": "rp-pppoe",
    "ip": "iproute2",
    "pppd": "ppp"
}

def check_root() -> bool:
    """Check if the script is running with root privileges."""
    return os.geteuid() == 0

def check_dependencies() -> Tuple[List[str], List[str]]:
    """
    Check for required system binaries.
    Returns (present_list, missing_list).
    """
    present = []
    missing = []
    for binary, package in REQUIRED_PACKAGES.items():
        if shutil.which(binary):
            present.append(binary)
        else:
            missing.append(binary)
            logger.error("Missing dependency: %s (install via package '%s')", binary, package)
    return present, missing
