import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner

from . import __version__
from .config import ISP_PRESETS, PPP_OPTIONS_TEMPLATE, LOG_FILE, BACKUP_DIR
from .logging_setup import setup_logging
from .restore import RollbackPlan
from .system.capabilities import check_root, check_dependencies
from .system.net import list_interfaces, setup_vlan, remove_vlan
from .system.files import backup_file, atomic_write, restore_file
from .pppoe.server import PPPoEServer
from .capture.tshark import TSharkCapture
from .parse.extract import parse_pap_line, mask_password

console = Console()

def print_banner():
    console.print(Panel(
        f"[bold cyan]PPPoE Credential Capture Helper[/bold cyan] v{__version__}\n"
        "[dim]Professional & Hardened ISP Router Replacement Tool[/dim]",
        expand=False
    ))

def get_authorized_consent(no_tty: bool = False) -> bool:
    if no_tty:
        return False
    console.print("\n[bold yellow]AUTHORIZATION REQUIRED[/bold yellow]")
    console.print("This tool is for authorized use only by subscribers to retrieve their own credentials.")
    response = console.input("[bold red]Are you authorized to capture these credentials? (y/N): [/bold red]")
    return response.lower() == 'y'

def main():
    parser = argparse.ArgumentParser(description="Capture PPPoE credentials safely.")
    parser.add_argument("--interface", help="Ethernet interface (e.g., eth0)")
    parser.add_argument("--isp", help="ISP preset name (e.g., digi, movistar)")
    parser.add_argument("--vlan", type=int, help="Override VLAN ID (use --no-vlan for untagged)")
    parser.add_argument("--no-vlan", action="store_true", help="Do not create a VLAN subinterface (use native/untagged)")
    parser.add_argument("--timeout", type=int, default=120, help="Capture timeout in seconds")
    parser.add_argument("--dry-run", action="store_true", help="Perform no system changes")
    parser.add_argument("--json", action="store_true", help="Output result as JSON")
    parser.add_argument("--reveal-password", action="store_true", help="Show full password in output")
    parser.add_argument("--i-am-authorized", action="store_true", help="Skip authorization prompt")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--no-tty", action="store_true", help="Disable animations/spinners")
    
    args = parser.parse_args()

    if not args.json:
        print_banner()

    # 1. Permission & Dependency Checks
    if not check_root() and not args.dry_run:
        console.print("[bold red]Error: Root privileges required.[/bold red]")
        sys.exit(4)

    # Ensure log directory exists
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    logger = setup_logging(str(log_path), args.verbose)
    logger.info("Session started (version %s)", __version__)

    present, missing = check_dependencies()
    if missing:
        if not args.json:
            console.print(f"[bold red]Error: Missing dependencies: {', '.join(missing)}[/bold red]")
        sys.exit(3)

    # 2. Authorization
    if not args.i_am_authorized and not get_authorized_consent(args.no_tty):
        console.print("[bold red]Error: Authorization not confirmed. Exiting.[/bold red]")
        sys.exit(1)

    # 3. Configuration
    iface = args.interface
    if not iface:
        interfaces = list_interfaces()
        if not interfaces:
            console.print("[bold red]Error: No ethernet interfaces found.[/bold red]")
            sys.exit(6)
        if len(interfaces) == 1:
            iface = interfaces[0]
        else:
            if not args.json:
                console.print("\n[bold cyan]Select Interface:[/bold cyan]")
                for i, name in enumerate(interfaces, 1):
                    console.print(f" [ {i} ] {name}")
                idx = int(console.input("Choice: ")) - 1
                iface = interfaces[idx]
            else:
                iface = interfaces[0]

    vlan: Optional[int] = args.vlan
    if args.no_vlan:
        vlan = None
    if vlan is None:
        if args.isp:
            for preset in ISP_PRESETS:
                if args.isp.lower() in preset.name.lower():
                    vlan = preset.vlan
                    break
        
        if vlan is None and not args.json:
            console.print("\n[bold cyan]Select ISP / VLAN:[/bold cyan]")
            for i, p in enumerate(ISP_PRESETS, 1):
                console.print(f" [ {i} ] {p.name} (VLAN {p.vlan})")
            no_vlan_idx = len(ISP_PRESETS) + 1
            manual_idx = len(ISP_PRESETS) + 2
            console.print(f" [ {no_vlan_idx} ] No VLAN (native/untagged)")
            console.print(f" [ {manual_idx} ] Manual VLAN")
            choice = int(console.input("Choice: "))
            if choice <= len(ISP_PRESETS):
                vlan = ISP_PRESETS[choice-1].vlan
            elif choice == no_vlan_idx:
                vlan = None
            else:
                vlan = int(console.input("Enter VLAN ID: "))
        # For non-interactive / JSON, default to untagged if nothing provided

    # 4. System Changes with Rollback
    rollback = RollbackPlan()
    try:
        with rollback:
            # VLAN Setup
            if vlan is None:
                vlan_iface = iface
                logger.info("Using native interface %s (no VLAN)", iface)
            else:
                vlan_iface = setup_vlan(iface, vlan, args.dry_run)
                rollback.push(f"Remove VLAN {vlan_iface}", remove_vlan, vlan_iface, args.dry_run)

            # PPP Options Setup
            options_path = Path("/etc/ppp/options")
            bak = backup_file(options_path, Path(BACKUP_DIR))
            if bak:
                rollback.push("Restore /etc/ppp/options", restore_file, options_path, bak, args.dry_run)
            
            atomic_write(options_path, PPP_OPTIONS_TEMPLATE, args.dry_run)

            # PAP Secrets (minimal addition)
            pap_path = Path("/etc/ppp/pap-secrets")
            pap_bak = backup_file(pap_path, Path(BACKUP_DIR))
            if pap_bak:
                rollback.push("Restore /etc/ppp/pap-secrets", restore_file, pap_path, pap_bak, args.dry_run)
            
            pap_line = '"Username"\t*\t"p4ssw0rd"\t*\n'
            if pap_path.exists():
                content = pap_path.read_text()
                if pap_line not in content:
                    with pap_path.open("a") as f:
                        if not args.dry_run: f.write(pap_line)
            else:
                atomic_write(pap_path, pap_line, args.dry_run)

            # Start Servers
            server = PPPoEServer(vlan_iface, str(options_path))
            server.start(args.dry_run)
            rollback.push("Stop PPPoE Server", server.stop, args.dry_run)

            capture = TSharkCapture(vlan_iface)
            
            if not args.json:
                console.print(f"\n[bold green]Ready to capture on {vlan_iface}[/bold green]")
                console.print("Connect the router's WAN port to your PC and power it on.")
                if not args.no_tty:
                    console.input("Press ENTER to start searching...")

            # 5. Capture Loop
            start_time = time.time()
            credentials = None
            
            with Live(Spinner("dots", text="Searching for credentials...") if not args.no_tty else None, console=console) as live:
                lines = capture.start(args.dry_run)
                for line in lines:
                    if time.time() - start_time > args.timeout:
                        break
                    
                    credentials = parse_pap_line(line)
                    if credentials:
                        break

            capture.stop(args.dry_run)

            # 6. Output Result
            if credentials:
                output = {
                    "status": "success",
                    "username": credentials.username,
                    "password_masked": mask_password(credentials.password),
                    "vlan": vlan,
                    "interface": iface
                }
                if args.reveal_password:
                    output["password"] = credentials.password

                if args.json:
                    print(json.dumps(output))
                else:
                    console.print("\n[bold green]SUCCESS: Credentials Found![/bold green]")
                    table = Table(show_header=False, box=None)
                    table.add_row("Username", f"[bold white]{credentials.username}[/bold white]")
                    pass_display = credentials.password if args.reveal_password else mask_password(credentials.password)
                    table.add_row("Password", f"[bold white]{pass_display}[/bold white]")
                    console.print(table)
            else:
                if args.json:
                    print(json.dumps({"status": "timeout", "error": "No credentials captured within timeout"}))
                else:
                    console.print("\n[bold red]FAILED: Timeout reached without capturing credentials.[/bold red]")
                sys.exit(5)

    except KeyboardInterrupt:
        if not args.json:
            console.print("\n[bold yellow]Interrupted by user. Cleaning up...[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        logger.exception("Runtime error")
        if not args.json:
            console.print(f"\n[bold red]Runtime Error: {e}[/bold red]")
        sys.exit(6)

if __name__ == "__main__":
    main()
