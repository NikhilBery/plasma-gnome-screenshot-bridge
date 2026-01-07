#!/usr/bin/env python3
"""
Plasma GNOME Screenshot Bridge

A DBus bridge that implements the GNOME Shell Screenshot interface for KDE Plasma
and other Wayland compositors. This enables applications that expect GNOME's
screenshot API (like Upwork, various time trackers, etc.) to work on Wayland.

Based on concepts from:
- https://github.com/MarSoft/upwork-wayland
- https://github.com/DrSh4dow/upwork-wlroots-bridge

Adapted for KDE Plasma with multi-backend support.
"""

import argparse
import asyncio
from datetime import datetime, timezone
import logging
import shutil
import signal
import subprocess
import sys
from typing import List, Optional

from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method

from . import __version__

logger = logging.getLogger(__name__)


class ScreenshotBackend:
    """Abstract base for screenshot backends."""
    name: str = "base"

    @classmethod
    def is_available(cls) -> bool:
        raise NotImplementedError

    @classmethod
    def capture_full(cls, filename: str, include_cursor: bool = False) -> bool:
        raise NotImplementedError

    @classmethod
    def capture_area(cls, filename: str, x: int, y: int, width: int, height: int) -> bool:
        raise NotImplementedError

    @classmethod
    def capture_window(cls, filename: str, include_cursor: bool = False,
                       include_decorations: bool = True) -> bool:
        raise NotImplementedError


class SpectacleBackend(ScreenshotBackend):
    """KDE Spectacle screenshot backend."""
    name = "spectacle"

    @classmethod
    def is_available(cls) -> bool:
        return shutil.which("spectacle") is not None

    @classmethod
    def capture_full(cls, filename: str, include_cursor: bool = False) -> bool:
        cmd = ["spectacle", "-b", "-n", "-f", "-o", filename]
        if include_cursor:
            cmd.append("-p")
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    @classmethod
    def capture_area(cls, filename: str, x: int, y: int, width: int, height: int) -> bool:
        logger.warning("Spectacle doesn't support coordinate-based area capture, "
                      "capturing full screen instead")
        return cls.capture_full(filename)

    @classmethod
    def capture_window(cls, filename: str, include_cursor: bool = False,
                       include_decorations: bool = True) -> bool:
        cmd = ["spectacle", "-b", "-n", "-a", "-o", filename]
        if include_cursor:
            cmd.append("-p")
        if not include_decorations:
            cmd.append("-e")
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0


class GrimBackend(ScreenshotBackend):
    """Grim screenshot backend for wlroots-based compositors."""
    name = "grim"

    @classmethod
    def is_available(cls) -> bool:
        return shutil.which("grim") is not None

    @classmethod
    def capture_full(cls, filename: str, include_cursor: bool = False) -> bool:
        cmd = ["grim"]
        if include_cursor:
            cmd.append("-c")
        cmd.append(filename)
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    @classmethod
    def capture_area(cls, filename: str, x: int, y: int, width: int, height: int) -> bool:
        cmd = ["grim", "-g", f"{x},{y} {width}x{height}", filename]
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    @classmethod
    def capture_window(cls, filename: str, include_cursor: bool = False,
                       include_decorations: bool = True) -> bool:
        logger.warning("Grim doesn't support window capture, capturing full screen")
        return cls.capture_full(filename, include_cursor)


class GnomeScreenshotBackend(ScreenshotBackend):
    """GNOME Screenshot backend (fallback)."""
    name = "gnome-screenshot"

    @classmethod
    def is_available(cls) -> bool:
        return shutil.which("gnome-screenshot") is not None

    @classmethod
    def capture_full(cls, filename: str, include_cursor: bool = False) -> bool:
        cmd = ["gnome-screenshot", "-f", filename]
        if include_cursor:
            cmd.append("-p")
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0

    @classmethod
    def capture_area(cls, filename: str, x: int, y: int, width: int, height: int) -> bool:
        return cls.capture_full(filename)

    @classmethod
    def capture_window(cls, filename: str, include_cursor: bool = False,
                       include_decorations: bool = True) -> bool:
        cmd = ["gnome-screenshot", "-w", "-f", filename]
        if include_cursor:
            cmd.append("-p")
        if not include_decorations:
            cmd.append("-B")
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0


BACKENDS: List[type] = [
    SpectacleBackend,
    GrimBackend,
    GnomeScreenshotBackend,
]


def detect_backend(preferred: Optional[str] = None) -> Optional[ScreenshotBackend]:
    """Detect and return an available screenshot backend."""
    if preferred:
        for backend_cls in BACKENDS:
            if backend_cls.name == preferred:
                if backend_cls.is_available():
                    logger.info(f"Using preferred backend: {backend_cls.name}")
                    return backend_cls
                else:
                    logger.warning(f"Preferred backend '{preferred}' not available")
                break

    for backend_cls in BACKENDS:
        if backend_cls.is_available():
            logger.info(f"Auto-detected backend: {backend_cls.name}")
            return backend_cls

    return None


class ScreenshotInterface(ServiceInterface):
    """DBus interface implementing org.gnome.Shell.Screenshot"""

    def __init__(self, backend: ScreenshotBackend, warn_before: bool = False):
        super().__init__("org.gnome.Shell.Screenshot")
        self.backend = backend
        self.warn_before = warn_before

    def _maybe_warn(self):
        if self.warn_before:
            try:
                subprocess.run([
                    "notify-send", "-u", "normal", "-t", "2000",
                    "Screenshot", "A screenshot will be taken..."
                ], capture_output=True)
            except Exception:
                pass

    @method()
    def Screenshot(self, include_cursor: 'b', flash: 'b', filename: 's') -> 'bs':
        logger.info(f"Screenshot requested: cursor={include_cursor}, file={filename}")
        self._maybe_warn()
        try:
            success = self.backend.capture_full(filename, include_cursor)
            logger.info(f"Screenshot {'saved' if success else 'failed'}: {filename}")
            return [success, filename]
        except Exception as e:
            logger.exception(f"Screenshot error: {e}")
            return [False, filename]

    @method()
    def ScreenshotWindow(self, include_frame: 'b', include_cursor: 'b',
                         flash: 'b', filename: 's') -> 'bs':
        logger.info(f"Window screenshot requested: file={filename}")
        self._maybe_warn()
        try:
            success = self.backend.capture_window(filename, include_cursor, include_frame)
            logger.info(f"Window screenshot {'saved' if success else 'failed'}: {filename}")
            return [success, filename]
        except Exception as e:
            logger.exception(f"Window screenshot error: {e}")
            return [False, filename]

    @method()
    def ScreenshotArea(self, x: 'i', y: 'i', width: 'i', height: 'i',
                       flash: 'b', filename: 's') -> 'bs':
        logger.info(f"Area screenshot requested: ({x},{y}) {width}x{height}")
        self._maybe_warn()
        try:
            success = self.backend.capture_area(filename, x, y, width, height)
            logger.info(f"Area screenshot {'saved' if success else 'failed'}: {filename}")
            return [success, filename]
        except Exception as e:
            logger.exception(f"Area screenshot error: {e}")
            return [False, filename]


class IdleMonitorInterface(ServiceInterface):
    """DBus interface implementing org.gnome.Mutter.IdleMonitor"""

    def __init__(self):
        super().__init__("org.gnome.Mutter.IdleMonitor")
        self.last_active = datetime.now(timezone.utc)
        self._monitor_process: Optional[asyncio.subprocess.Process] = None
        self._monitor_task: Optional[asyncio.Task] = None

    async def start_monitoring(self):
        """Start idle monitoring."""
        # Try swayidle first
        if shutil.which("swayidle"):
            try:
                self._monitor_process = await asyncio.create_subprocess_exec(
                    "swayidle", "-w",
                    "timeout", "1", "echo timeout",
                    "resume", "echo resume",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                self._monitor_task = asyncio.create_task(self._idle_loop())
                logger.info("Started swayidle idle monitor")
                return True
            except Exception as e:
                logger.debug(f"Failed to start swayidle: {e}")

        logger.warning("No idle monitor available, idle time will not be tracked")
        return False

    async def _idle_loop(self):
        if not self._monitor_process or not self._monitor_process.stdout:
            return
        try:
            async for line in self._monitor_process.stdout:
                if line.decode().strip() == "resume":
                    self.last_active = datetime.now(timezone.utc)
        except Exception as e:
            logger.debug(f"Idle monitor loop error: {e}")

    async def stop_monitoring(self):
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        if self._monitor_process:
            self._monitor_process.terminate()
            await self._monitor_process.wait()

    @method()
    def GetIdletime(self) -> 't':
        delta = datetime.now(timezone.utc) - self.last_active
        idle_ms = round(delta.total_seconds() * 1000)
        logger.debug(f"Idle time: {idle_ms}ms")
        return idle_ms


class ScreenshotBridge:
    """Main bridge application."""

    def __init__(self, backend: Optional[str] = None,
                 warn_before: bool = False, enable_idle: bool = True):
        self.backend_name = backend
        self.warn_before = warn_before
        self.enable_idle = enable_idle
        self.bus: Optional[MessageBus] = None
        self.idle_monitor: Optional[IdleMonitorInterface] = None
        self._running = False

    async def start(self):
        backend = detect_backend(self.backend_name)
        if not backend:
            logger.error("No screenshot backend available!")
            logger.error("Install one of: spectacle (KDE), grim (wlroots)")
            return False

        self.bus = MessageBus()
        await self.bus.connect()
        logger.info("Connected to DBus session bus")

        screenshot_iface = ScreenshotInterface(backend, self.warn_before)
        self.bus.export("/org/gnome/Shell/Screenshot", screenshot_iface)
        await self.bus.request_name("org.gnome.Shell.Screenshot")
        logger.info("Registered org.gnome.Shell.Screenshot")

        if self.enable_idle:
            self.idle_monitor = IdleMonitorInterface()
            await self.idle_monitor.start_monitoring()
            self.bus.export("/org/gnome/Mutter/IdleMonitor/Core", self.idle_monitor)
            await self.bus.request_name("org.gnome.Mutter.IdleMonitor")
            logger.info("Registered org.gnome.Mutter.IdleMonitor")

        self._running = True
        logger.info(f"Bridge started with backend: {backend.name}")
        return True

    async def run_forever(self):
        if not self._running:
            if not await self.start():
                return
        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def stop(self):
        self._running = False
        if self.idle_monitor:
            await self.idle_monitor.stop_monitoring()
        if self.bus:
            self.bus.disconnect()
        logger.info("Bridge stopped")


def setup_logging(verbose: bool = False, debug: bool = False):
    level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="plasma-gnome-screenshot-bridge",
        description="DBus bridge implementing GNOME Screenshot interface for Wayland compositors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Auto-detect backend and run
  %(prog)s -b spectacle       Force KDE Spectacle backend
  %(prog)s -b grim            Force Grim backend (wlroots)
  %(prog)s -w                 Warn before screenshots
  %(prog)s -v                 Verbose output

Backends:
  spectacle         KDE Plasma
  grim              wlroots (Sway, Hyprland, etc.)
  gnome-screenshot  GNOME (fallback)
        """,
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-b", "--backend", choices=["spectacle", "grim", "gnome-screenshot"],
                        help="Screenshot backend (default: auto-detect)")
    parser.add_argument("-w", "--warn", action="store_true",
                        help="Show notification before screenshots")
    parser.add_argument("--no-idle", action="store_true", help="Disable idle monitoring")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-D", "--debug", action="store_true", help="Debug output")
    return parser.parse_args()


async def async_main(args: argparse.Namespace):
    bridge = ScreenshotBridge(
        backend=args.backend,
        warn_before=args.warn,
        enable_idle=not args.no_idle,
    )
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(bridge.stop()))
    await bridge.run_forever()


def main():
    args = parse_args()
    setup_logging(args.verbose, args.debug)
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
