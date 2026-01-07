#!/bin/bash
# Upwork Wayland Wrapper
# Launches Upwork on Wayland by forcing XWayland mode
#
# This script tricks Upwork into thinking it's running on X11,
# allowing it to use the plasma-gnome-screenshot-bridge for screenshots.

# Force X11 session type so Upwork thinks it's on X11
export XDG_SESSION_TYPE=x11

# Unset Wayland display to prevent Wayland detection
unset WAYLAND_DISPLAY

# Use X11 backend for Electron
export ELECTRON_OZONE_PLATFORM_HINT=x11

# Launch Upwork
exec /opt/Upwork/upwork "$@"
