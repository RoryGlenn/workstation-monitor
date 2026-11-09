# Verify Workstation Monitor

Run commands from the repository root with the project environment prepared as described in the README.

## Counters, permissions, providers, and settings

```sh
.venv/bin/python -m unittest discover -s tests -v
```

These checks include fixtures for first/zero/reset rates, CPU topology and resume, PID reuse, partial groups, denied fields, missing devices/sensors, GPU unsupported fields, and preference corruption. Live checks read memory and NVIDIA counters, use a disposable two-second single-thread CPU workload, and transfer 4 MiB over loopback. They do not start GPU workloads or change machine-wide settings.

## Real native flow and layout

From the local graphical session:

```sh
PYTHONPATH="$PWD:$PWD/tests" .venv/bin/python tests/native_flow.py
PYTHONPATH="$PWD:$PWD/tests" .venv/bin/python tests/layout_flow.py
.venv/bin/python tests/virtual_layout.py
```

The native flow exercises actual GTK controls, process details, pause/resume, saved-preference readback, a narrow window, 2,000 fixture processes, identity-safe selection, and clean close. The layout flow checks 1280×800 and 600×700 logical pixels, light/dark appearance, grouping/expansion, stable focus, minimize/restore, and shutdown. The 200% check uses a disposable Xvfb display to test the requested logical window dimensions independently of the physical monitor size. It requires a project-local `.native/usr/bin/Xvfb` and libXfont2, extracted from Ubuntu's `xvfb`, `xserver-common`, and `libxfont2` packages. This changes no host display settings and opens no TCP listener. Its screenshots are saved under `/tmp/workstation-monitor-*`; the displayed process names are fixtures, not the user's running app inventory. Hardware values remain live. These are automated native checks and visual inspection, not a human usability study.

## End-to-end overhead and retention

```sh
PYTHONPATH="$PWD" .venv/bin/python tests/benchmark.py \
  --seconds 1800 --output artifacts/benchmark-30min.json
```

This opens a real native overview for a five-minute warm-up followed by 30 measured minutes at one-second refresh (35 minutes total). Leave it open and unminimized. Results contain numeric timings, process counts, memory, and bounded history sizes; no process names, arguments, raw snapshots, or endpoints. A checkpoint is saved every minute. A runtime-source hash records whether the implementation stayed unchanged. The benchmark explicitly creates this local evidence file; the ordinary app never records sessions.

Startup and first valid rates are observed separately from steady state. Warm-up fills the five-minute history buffers; the following ten minutes are the CPU acceptance window. CPU uses the process CPU-time difference divided by elapsed wall time and online logical CPU count, so 1% total-machine CPU equals 20% of one logical CPU on a 20-logical-CPU host. Compare RSS, p95 collection, and interaction measurements against the design. Group/sort, main-thread update, and curve-drawing timings are distinct: update includes model work, and curve timing excludes compositor work. Fixture interaction tests do not prove live-system performance.

For startup including Python imports and application setup, run `PYTHONPATH="$PWD:$PWD/tests" .venv/bin/python tests/startup_check.py`. It launches three fresh native app processes with warm OS caches and records both the first usable window and valid rates in `artifacts/startup.json`. The sustained benchmark's internal window timings begin at application activation and exclude its earlier imports/registration; use the fresh-process check for the complete startup budget.

Shorter `--seconds` runs are diagnostics only and do not establish the ten-minute or 30-minute acceptance gates. Profile the same fixture flow with `MONITOR_PROFILE=1` when needed; profiling overhead is excluded from acceptance measurements. The default launcher/benchmark uses Cairo with unused GL/Vulkan backends disabled to avoid unnecessary driver allocations.

## Restricted runtime and provider failures

```sh
PYTHONPATH="$PWD:$PWD/tests" .venv/bin/python tests/offline_flow.py
PYTHONPATH="$PWD:$PWD/tests" .venv/bin/python tests/fault_flow.py
```

The offline test requires the installed `libseccomp.so.2`. It denies IPv4/IPv6 socket creation only inside its own disposable process; local desktop sockets remain available and host networking is unchanged. The native app must still show CPU, process, network-counter, storage, and GPU values. The fault flow uses fixture providers behind the real session workers and GTK interface to verify stale data, history gaps after recovery, unavailable GPU fields, corrupt preferences, denied individual fields, and continued navigation.
