# Workstation Monitor 0.1.0 validation

The initial implementation passed 23 core/provider tests, native GTK flows, offline/failure checks, layout inspection, and a measured 30-minute retention run after a five-minute warm-up. All 32 implementation tasks in the [OpenSpec change](../openspec/changes/build-local-task-manager/tasks.md) are complete.

The compatibility baseline was Ubuntu 24.04 GNOME/X11, Python 3.12, GTK 4.14, libadwaita 1.5, PyGObject 3.48, and psutil 5.9. Hardware identities, workstation captures, absolute home paths, raw samples, and diagnostic traces are not distributed in the public repository.

## Representative development results

These observations describe one development run, not a performance guarantee for every machine or view. Reproduce the measurements on the intended host using [the test instructions](../tests/README.md).

| Measurement | Observed result |
| --- | --- |
| Fresh warm-cache process startup, including imports | Usable window in 0.62–0.75 s; valid rates in 1.49–1.53 s |
| Mean app CPU over a 600-second window | 0.725% of total machine capacity |
| Peak process RSS during the retention run | 180.11 MiB |
| RSS trend / largest rolling ten-minute increase | 1.218 / 4.277 MiB per ten minutes |
| p95 system/process collection | 207.35 ms |
| p95 GPU query / overview grouping / main-thread update | 2.41 / 9.39 / 27.98 ms |
| p95 curve-drawing callback | 0.54 ms |
| 2,000-process native fixture search/sort | Approximately 114 ms p95 |
| Retention and provider health | Bounded history, no recorded provider failures, unchanged runtime source hash |

The native inventory fixture does not establish live-system performance at that process count. Main-thread update timing includes model work; curve-drawing timing excludes compositor work. Process CPU/RSS includes worker threads and benchmark instrumentation. Startup and steady-state costs were measured separately. No GPU stress workload or active-job restart was used.

## Native and failure checks

- Overview-to-resource navigation, process search/details, numeric sorting, app expansion, stable focus/selection, frozen-view navigation, pause/resume, preference readback in a fresh process, and clean shutdown passed.
- Wide and narrow layouts at 1280×800 and 600×700 logical pixels passed in light/dark appearance. The 200% check used a disposable virtual X11 display rather than changing host display settings.
- Denied individual fields, corrupt preferences, slow/failed GPU queries, stale labels, gap preservation after recovery, device/interface changes, and simulated resume were checked with scoped fixtures.
- The real app continued with IPv4/IPv6 socket creation denied inside its own test process. A scoped syscall trace showed no IPv4/IPv6 connect or bind attempts. Link metadata became unknown while readable counters and other values continued.
- The user-local desktop entry opened a mapped window as the ordinary user. Closing exited its process without a child collector or autostart entry.
- Strict OpenSpec validation and source/documentation checks passed.

These are automated native tests plus visual inspection, not a human usability study or a screen-reader certification. Tests and benchmarks explicitly create local evidence files under ignored output directories; ordinary app operation does not record measurements.

## Implementation trade-offs

Profiling the large native inventory fixture identified costly per-cell widget setup/update. Shared GTK cell renderers and cached text brought that flow below its response target. GTK 4.14 supports the chosen renderer API, but it was deprecated in GTK 4.10; a future major-version migration needs a deliberate replacement with the same behavior checks.

Matched short diagnostic runs motivated using Cairo with unused GL/Vulkan backends disabled. GPU monitoring remains active. Those short runs motivated the renderer configuration rather than establishing a general end-to-end speedup.

## Requirement coverage

| Capability / requirement | Verification |
| --- | --- |
| Applications: searchable process inventory | Native search, numeric sort, and owner control; 2,000-process fixture flow |
| Applications: reliable application grouping | Scope/desktop match fixtures, same-name separation, live group count, native expansion |
| Applications: honest application totals | Partial-I/O aggregate and RSS fixtures; visible labels and detail text |
| Applications: field-level availability | Denied-I/O fixture keeps readable fields; live restricted processes remain listed |
| Applications: stable process identity | PID/start-time fixtures and native exited/reused-PID detail check |
| Applications: read-only details | Native detail flow; no signal/repriority APIs or default command-line/environment collection |
| Hardware: consistent CPU scale | Counter fixtures and disposable single-thread live workload normalized by online logical CPUs |
| Hardware: defined memory accounting | Live total-minus-available assertion and separate RSS/cache/swap fields |
| Hardware: NVIDIA device monitoring | Mock unsupported-field isolation and live driver readback; fault/recovery native flow |
| Hardware: storage usage and throughput | Partition/loop exclusion, disconnected-device fixtures, disposable fsynced local write, separate filesystem capacity |
| Hardware: reported sensors only | Missing-sensor fixture and live named sensor discovery |
| Hardware: honest history | Numeric scale/text checks, missing-interval history fixtures, native curve recorder and visual graphs |
| Network: interface activity | Real loopback transfer and matched counter deltas; link-metadata-denial fixture |
| Network: physical/virtual distinction | Per-interface type/state labels; named overview selection; no combined total |
| Network: lifecycle handling | Counter reset/disappearance fixtures with fresh baselines and disconnected state |
| Network: attribution boundary | Native labels/details and source inspection; no per-app bandwidth inference or packet capture |
| Network: history/availability | Valid-zero/reset fixtures, gaps after recovery, visible disconnected/unknown states |
| Session: refresh and pause | Native saved interval, pause/resume, frozen graph/value navigation |
| Session: valid baselines | First/zero/reset/elapsed fixtures, topology and simulated resume checks |
| Session: provider freshness | Native slow/failed GPU fixture while CPU/navigation continue |
| Session: bounded retention | Simulated 1,000-second history, selection change, and completed 30-minute live soak |
| Session: hidden/shutdown lifecycle | Native minimize/restore, virtual hide/restore, closing with settings/details, worker exit |
| Session: local privacy | IP-socket-denied native app, syscall trace, sanitized exception fixture, no runtime recording/listener code |
| Session: safe preferences | Allowlist, corrupt values, atomic write/permissions, readback and native settings flow |
| Session: live performance budget | Fresh-process startup, ten-minute total CPU, p95 collection, and final peak RSS all passed |
| Session: responsive long sessions | Native 2,000-row flow and final 30-minute soak passed |
| Interface: navigation | Real overview-to-resource and app/process detail flows |
| Interface: stable interaction | Native focus/selection/expansion checks with changing fixture rankings |
| Interface: adaptive layout | Inspected wide/narrow screenshots at 1× and 2× |
| Interface: accessible controls | Explicit control names, native keyboard focus/Escape, readable numeric labels, light/dark views |
| Interface: explanations | Visible CPU/RSS/partial/paused/stale labels, tooltip/help text, and user guide readback |
| Interface: desktop launch | Installed desktop metadata, ordinary-user mapped window, native close/process exit |

## Publication review

The public tree includes portable source, tests, documentation, and OpenSpec artifacts. Local environments, native binaries, caches, agent tooling, screenshots, settings, raw benchmark files, logs, and traces remain ignored. Follow the [publication checklist](publishing.md) before future pushes.

## Release boundaries

The application is local and read-only. Process termination, per-app network bandwidth, startup/service management, persistent recordings, remote access, and non-NVIDIA GPU adapters are outside this release. Visibility follows existing user permissions. Incomplete app metadata falls back to the process inventory.
