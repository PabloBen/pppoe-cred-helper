import logging
import netifaces
from typing import List, Optional
from .exec import run_command

logger = logging.getLogger("pppoe_cred_helper.system.net")

def list_interfaces() -> List[str]:
    """Return a list of physical-looking ethernet interfaces."""
    return [i for i in netifaces.interfaces() if i.startswith(("eth", "en", "p"))]

def setup_vlan(phys_iface: str, vlan_id: int, dry_run: bool = False) -> str:
    """
    Create a VLAN interface and assign it a local IP.
    Returns the name of the created interface.
    """
    vlan_iface = f"{phys_iface}.{vlan_id}"
    logger.info("Configuring VLAN interface: %s", vlan_iface)

    # Ensure it's clean (best effort)
    try:
        run_command(["ip", "link", "delete", vlan_iface], check=False, dry_run=dry_run, sudo=True)
    except Exception:
        pass

    run_command(
        ["ip", "link", "add", "link", phys_iface, "name", vlan_iface, "type", "vlan", "id", str(vlan_id)],
        dry_run=dry_run,
        sudo=True
    )
    run_command(["ip", "addr", "flush", "dev", vlan_iface], dry_run=dry_run, sudo=True)
    run_command(["ip", "addr", "add", "10.0.0.1/16", "dev", vlan_iface], dry_run=dry_run, sudo=True)
    run_command(["ip", "link", "set", vlan_iface, "up"], dry_run=dry_run, sudo=True)

    return vlan_iface

def remove_vlan(vlan_iface: str, dry_run: bool = False):
    """Remove a VLAN interface."""
    logger.info("Removing VLAN interface: %s", vlan_iface)
    run_command(["ip", "link", "delete", vlan_iface], check=False, dry_run=dry_run, sudo=True)
