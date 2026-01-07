# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
