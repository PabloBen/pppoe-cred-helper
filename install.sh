#!/usr/bin/env bash
set -euo pipefail

# Ensure root
if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  exec sudo "$0" "$@"
fi

echo "PPPoE Credential Capture Helper - Dependency Installer"
echo "======================================================"

if ! command -v apt-get >/dev/null 2>&1; then
  echo "Error: This installer currently supports apt-based systems only." >&2
  exit 1
fi

# Ensure universe repository (needed for some packages on Ubuntu)
if ! grep -Rqs '^[^#].*universe' /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null; then
  add-apt-repository -y universe
fi

# Preseed tshark setuid prompt (non-interactive)
if command -v debconf-set-selections >/dev/null 2>&1; then
  echo "wireshark-common wireshark-common/install-setuid boolean true" | debconf-set-selections
fi

echo "Updating package lists..."
apt-get update

echo "Installing system dependencies..."
apt-get install -y \
  tshark \
  ppp \
  ppp-dev \
  pppoeconf \
  build-essential \
  python3-pip \
  python3-netifaces \
  python3-rich \
  rp-pppoe \
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
    make && make install
  else
    echo "Warning: Could not source pppoe-server. Please install it manually if needed." >&2
  fi
fi

echo "Installing python package locally..."
pip3 install . --break-system-packages || pip3 install .

echo "------------------------------------------------------"
echo "Installation complete!"
echo "Run the tool with: sudo pppoe-cred-helper"
echo "For more info: pppoe-cred-helper --help"
