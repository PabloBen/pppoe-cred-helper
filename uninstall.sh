#!/usr/bin/env bash
set -euo pipefail

# Use sudo only for privileged removals
SUDO=""
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "Error: This uninstaller needs privilege to remove system installs; run as root or install sudo." >&2
    exit 1
  fi
fi

echo "PPPoE Credential Capture Helper - Uninstaller"
echo "============================================="

INSTALL_PREFIX=${INSTALL_PREFIX:-/usr/local}
PKG="pppoe-cred-helper"
APP_DIR="$INSTALL_PREFIX/share/pppoe-cred-helper"
LAUNCHER="$INSTALL_PREFIX/bin/pppoe-cred-helper"

echo "Removing installed script payload..."
if [[ -d "$APP_DIR" ]]; then
  $SUDO rm -rf "$APP_DIR"
  echo "  Removed $APP_DIR"
else
  echo "  Payload directory not found; skipping."
fi

echo "Removing leftover binaries..."
bin_candidates=(
  "$LAUNCHER"
  "$HOME/.local/bin/pppoe-cred-helper"
  "/usr/local/bin/pppoe-cred-helper"
  "/usr/bin/pppoe-cred-helper"
)

for path in "${bin_candidates[@]}"; do
  if [[ -e "$path" ]]; then
    if [[ -w "$path" ]]; then
      rm -f "$path"
    else
      $SUDO rm -f "$path"
    fi
    echo "  Removed $path"
  fi
done

echo "------------------------------------------------------"
echo "Uninstall complete."
echo "System dependencies installed by install.sh were left in place."
