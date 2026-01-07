#!/bin/bash
# Upwork Wayland Wrapper
# Launches Upwork on native Wayland with patched screenshot support
#
# This script runs Upwork on native Wayland but hides environment variables
# so the JavaScript isWayland() check returns false. Combined with the
# app.asar patch (see patch-upwork.sh), this enables working screenshots
# using spectacle on KDE Plasma Wayland.
#
# Requirements:
# - Upwork must be patched with patch-upwork.sh first
# - spectacle must be installed (for KDE Plasma)

# Save wayland socket for Electron to connect
WAYLAND_SOCK="$WAYLAND_DISPLAY"

# Hide Wayland from JavaScript environment checks
unset WAYLAND_DISPLAY
export XDG_SESSION_TYPE=x11

# Force Wayland via command line (overrides env vars for Electron internals)
# This allows Electron to run on native Wayland while JS thinks it's X11
exec /opt/Upwork/upwork \
    --enable-features=WebRTCPipeWireCapturer,UseOzonePlatform \
    --ozone-platform=wayland \
    --wayland-display="$WAYLAND_SOCK" \
    "$@"
