#!/usr/bin/env bash
set -euo pipefail

# Use sudo for privileged operations only
SUDO=""
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "Error: This installer must perform privileged operations; please run as root or install sudo." >&2
    exit 1
  fi
fi

echo "PPPoE Credential Capture Helper - Dependency Installer"
echo "======================================================"

# Allow overriding the installation prefix; defaults to /usr/local so sudo finds the CLI
INSTALL_PREFIX=${INSTALL_PREFIX:-/usr/local}
APP_DIR="$INSTALL_PREFIX/share/pppoe-cred-helper"
BIN_DIR="$INSTALL_PREFIX/bin"
LAUNCHER="$BIN_DIR/pppoe-cred-helper"

if ! command -v apt-get >/dev/null 2>&1; then
  echo "Error: This installer currently supports apt-based systems only." >&2
  exit 1
fi

# Ensure universe repository (needed for some packages on Ubuntu)
if ! grep -Rqs '^[^#].*universe' /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null; then
  $SUDO add-apt-repository -y universe
fi

# Preseed tshark setuid prompt (non-interactive)
if command -v debconf-set-selections >/dev/null 2>&1; then
  echo "wireshark-common wireshark-common/install-setuid boolean true" | $SUDO debconf-set-selections
fi

echo "Updating package lists..."
$SUDO apt-get update

echo "Installing system dependencies..."
$SUDO apt-get install -y \
  tshark \
  ppp \
  ppp-dev \
  pppoeconf \
  build-essential \
  python3-pip \
  python3-netifaces \
  python3-rich \
  curl \
  ca-certificates

# Build rp-pppoe from source if pppoe-server is missing (sometimes not in pkgs)
if ! command -v pppoe-server >/dev/null 2>&1; then
  echo "pppoe-server not found in packages; building from official source..." >&2
  tmpdir=$(mktemp -d)
  trap 'rm -rf "$tmpdir"' EXIT
  cd "$tmpdir"

  url=$(curl -fsSL https://dianne.skoll.ca/projects/rp-pppoe/download/ | \
    awk -F'"' '/href=.*tar.gz/ && $0 !~ /sig/ {print $2}' | tail -n1)

  if [[ -n "$url" ]]; then
    curl -fsSLO "https://dianne.skoll.ca/projects/rp-pppoe/download/$url"
    tar xvf "$url"
    src_dir="${url%.tar.gz}/src"
    cd "$src_dir"
    ./configure --enable-plugin
    make && $SUDO make install
  else
    echo "Warning: Could not source pppoe-server. Please install it manually if needed." >&2
  fi
fi

echo "Installing Python script (no package install)..."
$SUDO rm -rf "$APP_DIR"
$SUDO mkdir -p "$APP_DIR" "$BIN_DIR"
$SUDO cp -r pppoe_cred_helper "$APP_DIR"/
# Keep single-file helper for convenience (not required but useful)
if [[ -f pppoe.py ]]; then
  $SUDO cp pppoe.py "$APP_DIR"/
fi

cat > /tmp/pppoe-cred-helper-launcher <<EOF
#!/usr/bin/env python3
import os, sys, runpy
APP_DIR = "${APP_DIR}"
if not os.path.isdir(APP_DIR):
    sys.stderr.write(f"Error: application directory not found at {APP_DIR}\\n")
    sys.exit(1)
sys.path.insert(0, APP_DIR)
runpy.run_module("pppoe_cred_helper.cli", run_name="__main__")
EOF
$SUDO mv /tmp/pppoe-cred-helper-launcher "$LAUNCHER"
$SUDO chmod +x "$LAUNCHER"

if ! command -v pppoe-cred-helper >/dev/null 2>&1; then
  echo "Note: Installed launcher at $LAUNCHER but it is not on your PATH."
  echo "Add $BIN_DIR to PATH (or sudoers secure_path) to invoke it as 'pppoe-cred-helper'."
fi

echo "------------------------------------------------------"
echo "Installation complete!"
echo "Run the tool with: sudo pppoe-cred-helper (or python $LAUNCHER)"
echo "For more info: pppoe-cred-helper --help"
