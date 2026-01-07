#!/bin/bash
# Installation script for plasma-gnome-screenshot-bridge

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Plasma GNOME Screenshot Bridge Installer ==="
echo

# Check Python version
python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $python_version"

# Check for required tools
echo "Checking dependencies..."

check_command() {
    if command -v "$1" &> /dev/null; then
        echo "  ✓ $1 found"
        return 0
    else
        echo "  ✗ $1 not found"
        return 1
    fi
}

# Check screenshot backends
backends_found=0
check_command spectacle && backends_found=1
check_command grim && backends_found=1
check_command gnome-screenshot && backends_found=1

if [ $backends_found -eq 0 ]; then
    echo
    echo "ERROR: No screenshot backend found!"
    echo "Please install one of:"
    echo "  - spectacle (KDE Plasma)"
    echo "  - grim (wlroots/Sway/Hyprland)"
    echo "  - gnome-screenshot (GNOME)"
    exit 1
fi

echo

# Install the package
echo "Installing plasma-gnome-screenshot-bridge..."
if command -v uv &> /dev/null; then
    uv pip install "$PROJECT_DIR"
else
    pip install --user "$PROJECT_DIR"
fi

echo

# Install systemd service
echo "Installing systemd user service..."
mkdir -p ~/.config/systemd/user/
cp "$SCRIPT_DIR/plasma-gnome-screenshot-bridge.service" ~/.config/systemd/user/

echo

# Reload systemd
systemctl --user daemon-reload

# Create symlink for bridge binary if installed in venv
echo "Setting up binary symlink..."
mkdir -p ~/.local/bin
if [ -f "$PROJECT_DIR/../.venv/bin/plasma-gnome-screenshot-bridge" ]; then
    ln -sf "$PROJECT_DIR/../.venv/bin/plasma-gnome-screenshot-bridge" ~/.local/bin/
elif command -v plasma-gnome-screenshot-bridge &> /dev/null; then
    ln -sf "$(which plasma-gnome-screenshot-bridge)" ~/.local/bin/
fi

# Install Upwork wrapper (optional)
if [ -f /opt/Upwork/upwork ]; then
    echo "Upwork detected. Installing Wayland wrapper..."
    cp "$SCRIPT_DIR/upwork-wayland.sh" ~/.local/bin/upwork-wayland
    chmod +x ~/.local/bin/upwork-wayland

    # Install desktop file override with full path
    mkdir -p ~/.local/share/applications
    sed "s|Exec=upwork-wayland|Exec=$HOME/.local/bin/upwork-wayland|" \
        "$SCRIPT_DIR/upwork.desktop" > ~/.local/share/applications/upwork.desktop

    # Rebuild desktop database
    update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
    kbuildsycoca6 2>/dev/null || true

    echo "  ✓ Upwork wrapper installed"
fi

echo
echo "=== Installation Complete ==="
echo
echo "To start the service now:"
echo "  systemctl --user start plasma-gnome-screenshot-bridge"
echo
echo "To enable on login:"
echo "  systemctl --user enable plasma-gnome-screenshot-bridge"
echo
echo "To check status:"
echo "  systemctl --user status plasma-gnome-screenshot-bridge"
echo
echo "To run manually:"
echo "  plasma-gnome-screenshot-bridge -v"
echo
if [ -f /opt/Upwork/upwork ]; then
    echo "Upwork: Launch from application menu - it will use XWayland mode automatically."
fi
