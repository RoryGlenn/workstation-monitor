"""Use Ubuntu GI, with an optional project-local Ubuntu Cairo bridge."""

from pathlib import Path
import gi

bridge = Path(__file__).resolve().parents[1] / ".native/usr/lib/python3/dist-packages/gi"
if bridge.is_dir():
    gi.__path__.append(str(bridge))
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_foreign("cairo")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk, Pango  # noqa: E402
