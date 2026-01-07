# PPPoE Credential Capture Helper

A professional, hardened utility to capture PPPoE credentials sent by an ISP router. This tool is designed for authorized subscribers who wish to replace their ISP-provided router with their own equipment in FTTH setups.

## Safety & Hardening Features

- **Guaranteed Rollback**: All system changes (VLAN interfaces, file modifications) are automatically undone even on crash or Ctrl+C.
- **Dry Run Mode**: Use `--dry-run` to see what actions would be taken without modifying the system.
- **Secret Redaction**: Passwords are masked by default in all outputs and logs unless explicitly revealed with `--reveal-password`.
- **Atomic File Edits**: System configuration files are backed up and updated using atomic write operations.
- **Consent Gate**: Requires explicit authorization confirmation before proceeding.

## Requirements

- **OS**: Linux (Debian/Ubuntu-like)
- **Privileges**: Root/sudo access (for network and PPP configuration)
- **Dependencies**: `tshark`, `rp-pppoe`, `ppp`, `iproute2`
- **Python**: 3.8+ with `netifaces` and `rich`

## Installation (script-only, no pip package)

1. Clone or download this repository.
2. Install system dependencies and place the script under `/usr/local/bin` (default):
   ```bash
   ./install.sh
   ```
   (script uses sudo only where required)

## Uninstall

Remove the installed script:
```bash
./uninstall.sh
```

## Usage

### Basic Usage (Interactive)
```bash
sudo pppoe-cred-helper
```

### Advanced Usage (Flags)
```bash
sudo pppoe-cred-helper --interface eth0 --isp digi --timeout 300 --reveal-password
```

### Options
- `--interface`: Specify the physical Ethernet interface (e.g., `eth0`).
- `--isp`: Use a preset for your ISP (e.g., `digi`, `movistar`, `vodafone`).
- `--vlan`: Manually specify the VLAN ID.
- `--no-vlan`: Skip VLAN creation and use the native (untagged) interface.
- `--timeout`: Capture timeout in seconds (default: 120).
- `--dry-run`: Do not perform any system changes.
- `--json`: Output result as a machine-readable JSON object.
- `--reveal-password`: Show the full captured password (masked by default).
- `--i-am-authorized`: Skip the interactive authorization prompt.
- `--no-tty`: Disable animations and spinners for non-interactive shells.

## Exit Codes
- `0`: Success
- `1`: Cancelled by user / No authorization
- `2`: Invalid arguments
- `3`: Missing dependency
- `4`: Permission/Root required
- `5`: Timeout / No credentials captured
- `6`: Runtime/System error

## Development & Testing

Run unit tests with:
```bash
PYTHONPATH=. pytest tests/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
