#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
# Cairo avoids a large GL driver allocation for this mostly static dashboard.
export GSK_RENDERER="${GSK_RENDERER:-cairo}"
if [ "$GSK_RENDERER" = cairo ]; then
    export GDK_DEBUG="${GDK_DEBUG:+$GDK_DEBUG,}gl-disable,vulkan-disable"
fi
exec .venv/bin/python -m workstation_monitor "$@"
