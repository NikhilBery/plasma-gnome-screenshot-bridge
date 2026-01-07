# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-01-07

### Added
- **Upwork Wayland Screenshot Support** - Complete solution for Upwork screenshots on Wayland
  - `contrib/patch-upwork.sh` - Script to patch Upwork's app.asar for Wayland screenshot support
  - Updated `contrib/upwork-wayland.sh` - Wrapper script for launching patched Upwork
  - `contrib/upwork.desktop` - Desktop entry for launching Upwork with Wayland support

### Technical Details - Upwork Wayland Fix

#### The Problem
Upwork's Linux client doesn't support screenshots on Wayland, showing "Wayland screenshots not supported" error. This is because:
1. Upwork's native module (`uta_native.node`) detects Wayland via multiple methods
2. When Wayland is detected, screenshot capture returns empty data
3. The native module uses X11 APIs that can't capture Wayland content

#### Approaches Tried (and why they failed)

1. **Environment Variable Hiding** (`XDG_SESSION_TYPE=x11`, `unset WAYLAND_DISPLAY`)
   - Result: First screenshot works, subsequent fail
   - Reason: Native module caches Wayland detection after first check

2. **Fake XDG_RUNTIME_DIR without Wayland Socket**
   - Result: Upwork detected as non-Wayland, but screenshots were black
   - Reason: Running on XWayland, X11 capture can't see Wayland windows

3. **D-Bus Proxy Filtering** (xdg-dbus-proxy to block KWin D-Bus)
   - Result: App crashed or failed to start
   - Reason: Too aggressive filtering broke other D-Bus dependencies

4. **xwaylandvideobridge**
   - Result: Black screenshots
   - Reason: Only works with PipeWire portal, not raw X11 capture

5. **Bubblewrap Sandbox**
   - Result: App stuck loading or crashed
   - Reason: Symlink issues with runtime directory mounting

6. **Electron desktopCapturer Patch**
   - Result: Black screenshots
   - Reason: With `--ozone-platform=x11`, desktopCapturer uses X11 which can't see Wayland

7. **Native Wayland + desktopCapturer Patch**
   - Result: "Wayland not supported" error returned
   - Reason: Environment variables still exposed, JS isWayland() check still triggered

#### Final Working Solution

The solution requires two components:

1. **JavaScript Patch** (`patch-upwork.sh`):
   - Replaces native screenshot code with `spectacle` invocation
   - Spectacle is KDE's native screenshot tool that works perfectly on Wayland
   - Bypasses the native module entirely for screen capture

2. **Wrapper Script** (`upwork-wayland.sh`):
   - Runs Upwork on native Wayland (`--ozone-platform=wayland`)
   - Hides `WAYLAND_DISPLAY` env var so JS `isWayland()` returns false
   - Passes Wayland socket via `--wayland-display` flag
   - Result: Electron runs native Wayland, but JS thinks it's X11

This combination allows spectacle to capture the real Wayland screen while
the JavaScript code path for screenshots is properly executed.

## [1.0.0] - 2026-01-07

### Added
- Initial release
- Support for KDE Plasma via `spectacle` backend
- Support for wlroots compositors (Sway, Hyprland, etc.) via `grim` backend
- Fallback support for GNOME via `gnome-screenshot` backend
- Implementation of `org.gnome.Shell.Screenshot` DBus interface
  - `Screenshot()` - Full screen capture
  - `ScreenshotWindow()` - Active window capture
  - `ScreenshotArea()` - Area capture
- Implementation of `org.gnome.Mutter.IdleMonitor` DBus interface
  - `GetIdletime()` - Returns idle time in milliseconds
- Auto-detection of available screenshot backends
- Optional warning notifications before screenshots
- Systemd user service for autostart
- Command-line interface with verbose/debug modes
- Comprehensive documentation
