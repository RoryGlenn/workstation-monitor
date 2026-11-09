"""An allowlist prevents runtime measurements from entering saved settings."""

import json
import os
from pathlib import Path
import tempfile

DEFAULTS = {"interval": 1, "appearance": "system"}


class Settings:
    def __init__(self, directory=None):
        base = directory or os.environ.get("WORKSTATION_MONITOR_CONFIG_DIR")
        self.directory = Path(base) if base else Path(os.environ.get(
            "XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "workstation-monitor"
        self.path = self.directory / "preferences.json"
        self.values = DEFAULTS.copy()
        self.warning = ""
        try:
            raw = json.loads(self.path.read_text())
            if not isinstance(raw, dict):
                raise ValueError()
            if type(raw.get("interval")) is not int or raw["interval"] not in (1, 2, 5):
                raise ValueError()
            if raw.get("appearance") not in ("system", "light", "dark"):
                raise ValueError()
            self.values = {k: raw[k] for k in DEFAULTS}
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError):
            self.warning = "Preferences could not be loaded. Safe defaults are in use."

    def save(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=self.directory, delete=False) as stream:
                temporary = stream.name
                json.dump({k: self.values[k] for k in DEFAULTS}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
        finally:
            if temporary and Path(temporary).exists():
                Path(temporary).unlink()
