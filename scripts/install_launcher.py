"""Install only this app's user-local wrapper, icon reference, and desktop entry."""

from pathlib import Path
import os
import shlex

root = Path(__file__).resolve().parents[1]
bindir = Path.home() / ".local/bin"
apps = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "applications"
bindir.mkdir(parents=True, exist_ok=True)
apps.mkdir(parents=True, exist_ok=True)
wrapper = bindir / "workstation-monitor"
desktop = apps / "local.workstation.Monitor.desktop"
marker = "Managed by Workstation Monitor"
for path in (wrapper, desktop):
    if path.exists() and marker not in path.read_text():
        raise SystemExit(f"Refusing to overwrite unrelated file: {path}")
wrapper.write_text(f"#!/bin/sh\n# {marker}\nexec {shlex.quote(str(root / 'run.sh'))} \"$@\"\n")
wrapper.chmod(0o755)
desktop.write_text(f"""[Desktop Entry]
# {marker}
Type=Application
Name=Workstation Monitor
Comment=See app usage and hardware performance on this computer
Exec="{wrapper}"
Icon={root / 'assets/monitor.svg'}
Terminal=false
Categories=System;Monitor;
StartupNotify=true
StartupWMClass=local.workstation.Monitor
""")
desktop.chmod(0o644)
print(wrapper)
print(desktop)
