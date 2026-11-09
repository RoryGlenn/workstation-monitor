#!/bin/sh
# Resolve public dependencies locally; never modify system Python or apt state.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
/usr/bin/python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
if ! .venv/bin/python -c 'from workstation_monitor.native import Gtk, Adw' >/dev/null 2>&1; then
    mkdir -p .cache/debs .native
    (cd .cache/debs && apt download python3-gi-cairo)
    for package in .cache/debs/python3-gi-cairo_*.deb; do
        dpkg-deb -x "$package" .native
    done
fi
.venv/bin/python -c 'from workstation_monitor.native import Gtk, Adw; import psutil; print("Native dependencies ready")'
