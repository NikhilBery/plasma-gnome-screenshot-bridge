# Plasma GNOME Screenshot Bridge

A DBus bridge that implements the GNOME Shell Screenshot interface (`org.gnome.Shell.Screenshot`) for **KDE Plasma** and other **Wayland compositors**. This enables legacy applications that expect GNOME's screenshot API to work on non-GNOME Wayland sessions.

## The Problem

Many applications (like Upwork, various time trackers, and other tools) use GNOME's DBus screenshot interface to capture screenshots. On Wayland, these applications fail on KDE Plasma, Sway, Hyprland, and other non-GNOME compositors because the expected DBus interface doesn't exist.

This bridge solves the problem by:
1. Registering the `org.gnome.Shell.Screenshot` DBus interface
2. Intercepting screenshot requests from applications
3. Using your compositor's native screenshot tool to capture the screen
4. Returning the result to the requesting application

## Supported Environments

| Compositor | Backend | Status |
|------------|---------|--------|
| KDE Plasma | `spectacle` | ✅ Full support |
| Sway | `grim` | ✅ Full support |
| Hyprland | `grim` | ✅ Full support |
| Other wlroots | `grim` | ✅ Full support |
| GNOME | `gnome-screenshot` | ⚠️ Fallback only |

## Installation

### Prerequisites

- Python 3.9+
- One of the screenshot backends:
  - **KDE Plasma**: `spectacle` (usually pre-installed)
  - **wlroots (Sway/Hyprland)**: `grim`
  - **GNOME**: `gnome-screenshot`

### Install from source

```bash
# Clone the repository
git clone https://github.com/numbery/plasma-gnome-screenshot-bridge.git
cd plasma-gnome-screenshot-bridge

# Install with pip
pip install --user .

# Or install in development mode
pip install --user -e .
```

### Install dependencies (Fedora)

```bash
# For KDE Plasma
sudo dnf install spectacle python3-pip

# For Sway/Hyprland
sudo dnf install grim python3-pip

# Python dependency (usually already installed)
pip install --user dbus-next
```

### Install dependencies (Arch Linux)

```bash
# For KDE Plasma
sudo pacman -S spectacle python-pip

# For Sway/Hyprland
sudo pacman -S grim python-pip

# Python dependency
pip install --user dbus-next
```

### Install dependencies (Ubuntu/Debian)

```bash
# For KDE Plasma
sudo apt install kde-spectacle python3-pip

# For Sway/Hyprland
sudo apt install grim python3-pip

# Python dependency
pip install --user dbus-next
```

## Usage

### Manual Start

```bash
# Run with auto-detected backend
plasma-gnome-screenshot-bridge

# Run with verbose output
plasma-gnome-screenshot-bridge -v

# Force a specific backend
plasma-gnome-screenshot-bridge -b spectacle
plasma-gnome-screenshot-bridge -b grim

# Show warning notification before screenshots
plasma-gnome-screenshot-bridge -w

# Show all options
plasma-gnome-screenshot-bridge --help
```

### Systemd Service (Recommended)

The bridge should run in the background whenever you're logged in. The easiest way is to use systemd:

```bash
# Copy the service file
mkdir -p ~/.config/systemd/user/
cp contrib/plasma-gnome-screenshot-bridge.service ~/.config/systemd/user/

# Reload systemd
systemctl --user daemon-reload

# Start the service
systemctl --user start plasma-gnome-screenshot-bridge

# Enable on login
systemctl --user enable plasma-gnome-screenshot-bridge

# Check status
systemctl --user status plasma-gnome-screenshot-bridge

# View logs
journalctl --user -u plasma-gnome-screenshot-bridge -f
```

### Autostart (Alternative)

If you prefer not to use systemd, add to your autostart:

**KDE Plasma:**
Create `~/.config/autostart/plasma-gnome-screenshot-bridge.desktop`:
```ini
[Desktop Entry]
Type=Application
Name=Screenshot Bridge
Exec=plasma-gnome-screenshot-bridge
Hidden=false
X-KDE-autostart-after=panel
```

**Sway:**
Add to `~/.config/sway/config`:
```
exec plasma-gnome-screenshot-bridge
```

**Hyprland:**
Add to `~/.config/hypr/hyprland.conf`:
```
exec-once = plasma-gnome-screenshot-bridge
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `-b, --backend` | Force a specific backend (`spectacle`, `grim`, `gnome-screenshot`) |
| `-w, --warn` | Show notification before taking screenshots |
| `--no-idle` | Disable idle time monitoring |
| `-v, --verbose` | Enable verbose output |
| `-D, --debug` | Enable debug output |
| `-V, --version` | Show version |

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Application                          │
│                    (Upwork, Time Tracker, etc.)                  │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                                  │ DBus call to
                                  │ org.gnome.Shell.Screenshot
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              plasma-gnome-screenshot-bridge                      │
│                                                                  │
│  • Implements org.gnome.Shell.Screenshot interface               │
│  • Implements org.gnome.Mutter.IdleMonitor interface             │
│  • Routes requests to native screenshot tool                     │
└─────────────────────────────────┬───────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
              ┌──────────┐ ┌──────────┐ ┌──────────────┐
              │ spectacle│ │   grim   │ │gnome-        │
              │  (KDE)   │ │(wlroots) │ │screenshot    │
              └──────────┘ └──────────┘ └──────────────┘
```

## Implemented DBus Interfaces

### org.gnome.Shell.Screenshot

| Method | Description |
|--------|-------------|
| `Screenshot(include_cursor, flash, filename)` | Capture full screen |
| `ScreenshotWindow(include_frame, include_cursor, flash, filename)` | Capture active window |
| `ScreenshotArea(x, y, width, height, flash, filename)` | Capture specific area |

### org.gnome.Mutter.IdleMonitor

| Method | Description |
|--------|-------------|
| `GetIdletime()` | Returns idle time in milliseconds |

## Troubleshooting

### "No screenshot backend available"

Install one of the supported screenshot tools:
```bash
# KDE Plasma
sudo dnf install spectacle  # Fedora
sudo pacman -S spectacle    # Arch

# Sway/Hyprland
sudo dnf install grim       # Fedora
sudo pacman -S grim         # Arch
```

### Screenshots not working in your application

1. Make sure the bridge is running:
   ```bash
   systemctl --user status plasma-gnome-screenshot-bridge
   ```

2. Test manually:
   ```bash
   plasma-gnome-screenshot-bridge -v -D
   ```

3. Check if the DBus interface is registered:
   ```bash
   dbus-send --session --print-reply \
     --dest=org.gnome.Shell.Screenshot \
     /org/gnome/Shell/Screenshot \
     org.gnome.Shell.Screenshot.Screenshot \
     boolean:false boolean:false string:/tmp/test.png
   ```

### Application still shows "Wayland not supported"

Some applications explicitly check for Wayland and refuse to work. In those cases:
1. Try setting `XDG_SESSION_TYPE=x11` before running the application
2. Run the application under XWayland
3. Contact the application developer to support Wayland properly

## Credits

This project is inspired by and based on:
- [MarSoft/upwork-wayland](https://github.com/MarSoft/upwork-wayland) - Python implementation for wlroots
- [DrSh4dow/upwork-wlroots-bridge](https://github.com/DrSh4dow/upwork-wlroots-bridge) - Rust implementation for wlroots

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

MIT License - see [LICENSE](LICENSE) for details.
