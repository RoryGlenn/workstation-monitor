# Design

## Context

See [proposal.md](proposal.md) for the problem and product scope. This began as a greenfield project: no application source, tests, or existing capability specifications were present before OpenSpec initialization. The architecture below defines the implemented design; budgets remain acceptance targets rather than assumed results. Current evidence belongs in the [validation report](../../../docs/validation.md).

The initial compatibility baseline was Ubuntu 24.04 GNOME/X11 with Python 3.12, GTK 4.14, libadwaita 1.5, PyGObject 3.48, and psutil 5.9. Hardware details, raw process observations, and workstation captures are kept outside the public repository.

Linux exposes basic process CPU and memory information more broadly than storage I/O. Some fields are permission restricted even when the rest of a process row is readable. Desktop application metadata also has incomplete coverage. These boundaries require field-level availability and a process fallback rather than elevation or guessed app grouping.

Discover CPUs, drives, interfaces, and sensors dynamically. Separate physical devices from partitions and virtual interfaces. The initial GPU adapter uses NVIDIA NVML and degrades gracefully when the library or a field is unavailable. The runtime also needs the compatible Cairo/PyGObject bridge described in the README.

## Goals / Non-Goals

**Goals:** Separate measurement from presentation; make rate calculations reproducible; remain usable when individual sources fail; support the actual machine without elevated permissions; establish end-to-end release gates before adding more features.

**Non-goals:** A browser-hosted dashboard, background service, generic cross-platform framework, root helper, packet capture, and sandbox distribution in the first release. Cross-platform collectors can be considered later without constraining the initial Ubuntu interface.

## Decisions

### 1. Native Python and GTK4 for the first release

| Option | Fit and trade-off | Decision |
| --- | --- | --- |
| Python + GTK4/libadwaita | The Ubuntu runtime packages provide native bindings; psutil exposes the needed counters; native widgets provide keyboard/accessibility support. Python polling and rendering overhead still need measurement. | Selected for the first release. |
| Rust + GTK4 | Credible native alternative with explicit ownership and thread safety, but requires a new build/dependency path and different collector integrations. No comparative benchmark exists. | Reconsider only if measured Python costs miss the budgets after focused improvements. |
| Tauri + web UI | Useful for web-style UI and broader desktop delivery, but introduces Rust/frontend/WebKit integration for a single-machine native tool. | Defer; the current scope does not need a web stack. |
| Existing GNOME System Monitor / btop | They provide useful reference tools for raw metrics. | Custom work is justified by the requested unified app, GPU, and network experience; do not reimplement unrelated administration features. |

Use the distribution's Python/GTK/GI compatibility baseline. During implementation, create a project virtual environment with access to system GI packages; avoid replacing system Python or installing a newer PyGObject into the OS. Record tested dependencies. The NVIDIA binding is the `nvidia-ml-py` distribution, imported as `pynvml`; initialize once and query read-only APIs. If unavailable, report the capability state and keep other views working. Do not spawn `nvidia-smi` on every refresh.

### 2. Collect immutable snapshots away from GTK

The data path is:

```text
Linux counters / sensors       NVIDIA NVML
           |                       |
     system sampler          GPU provider worker
           |                       |
           +--- timestamped values + availability ---+
                                                    |
                              latest snapshot + bounded history
                                                    |
                                 GTK main-loop presentation
```

Use a worker for system/process reads and an independent worker for the optional GPU provider. All GTK access stays on the main thread. Coalesce updates to one pending presentation callback and at most one in-flight poll per provider. Retain each provider's own timestamp; late GPU results must not make old data look current or block CPU/network updates. Repeated optional-provider failures use bounded retry/backoff and never accumulate more workers.

Snapshots carry monotonic sample times, wall-clock display times, durations, stable process/device identities, and a status alongside each optional value. Statuses distinguish warming up, available, permission denied, unsupported, unavailable, and stale. After two missed scheduled intervals, visibly mark a provider stale and show its last successful update time. Last-good values remain visibly stale; unavailable values never become numeric zero.

Default sampling is one second; offer 1, 2, and 5 seconds. When the window is not visible, sample no faster than every five seconds and stop repainting. “Pause display” freezes the visible snapshot while collection/history continue; the banner explains this. Resume jumps to the latest data. Keep five minutes of device/overview history in time-bounded buffers; do not retain five minutes of every process. Keep current and previous process snapshots plus history for at most one selected process. Closing the app stops timers and workers without an indefinite wait or background daemon.

Proposed module boundaries are `collectors/`, `model/` (identity, rates, availability, bounded history), and `ui/`, with fixture tests separate from native desktop tests. These names are an implementation outline, not a requirement to create empty modules.

### 3. Define measurements before building graphs

| Measurement | Definition and presentation |
| --- | --- |
| CPU | Whole-machine and per-logical-CPU usage use 0–100%. Process CPU is delta user+system CPU seconds / monotonic elapsed / online logical CPU count × 100. One saturated logical CPU on a host with 20 logical CPUs is approximately 5% of whole-machine capacity. Reset the baseline after topology changes. |
| RAM | Headline used = total minus available; show available, cache, total, and swap separately. Do not label cache as an app's memory. |
| Process memory | Use resident set size (RSS), explicitly labeled. App totals sum member RSS and disclose shared-page double counting. PSS is a slower optional measurement for the selected process only, with its own availability state. |
| GPU | Separate device utilization (%) from VRAM used/total, temperature (°C), and power (W). Process VRAM appears only when the driver actually reports it; do not invent per-app GPU utilization or Windows GPU-engine parity. |
| Disk | Device read/write bytes per second, operations per second, and filesystem used/available capacity are separate. Process I/O means kernel-accounted storage read/write counters, not all application file operations. Avoid partition/device double counting. |
| Network | Per-interface receive/send counter deltas divided by actual elapsed time, displayed as KiB/s or MiB/s. Link speed, if known, is separately labeled Mbit/s. This is interface throughput, not an internet speed test. |
| Sensors | Show only reported sensors with names and units; no inferred fan RPM, temperatures, or health verdicts. |

For CPU and byte rates, the first sample is “Measuring…”. Reset, decrease, replacement, suspend/resume discontinuity, or failed identity validation invalidates the delta; seed a new baseline. A legitimate zero requires two valid samples. Byte sizes use IEC units throughout. Fixed percentage axes span 0–100; throughput graphs may autoscale with visible units and scale changes. Missing intervals remain gaps. Different monitoring tools may disagree because of sampling windows or definitions; validate raw counters and matched intervals before declaring a bug.

### 4. Treat app grouping as evidence-based presentation

The process inventory remains authoritative. Key process state by PID and start time within the current boot, not PID alone. Use desktop application IDs and user-session cgroup/scope metadata to associate processes with an app. Parent relationships can support a match only when they do not cross an established application boundary. A process belongs to at most one group; do not merge unrelated processes just because their executable names match.

Display apps with expandable members and aggregate CPU/RSS and readable I/O. A partially readable aggregate is labeled partial rather than presented as a complete total. Keep services and unmatched processes visible in the process view, retaining basic rows when optional fields fail. Generic browser renderer processes are grouped only when there is reliable metadata; no promise of tab-level attribution. Process details expose name, PID, owner, state, parent, threads, start time, and measurements. Do not collect environment variables or full command-line arguments by default.

### 5. Organize around everyday questions

| View | Main question | Controls and content |
| --- | --- | --- |
| Overview | What is busy right now? | CPU, memory, GPU, disk, and selected interface summaries with recent graphs; highest CPU/memory app rows link to details. |
| Apps | Which app is using resources? | Search, sort, grouped rows, expand members, process details; visible warning when a total is partial. |
| Processes | What is actually running? | Complete accessible inventory, sort/search, optional owner filter, stable selection. |
| Performance | Which hardware resource is under pressure? | Resource/device navigation; per-core CPU, memory, disks, GPU, temperatures, and network details. |

Global controls are “Pause display”, “Refresh interval”, and “Settings”. Do not add termination controls in this change. Explain CPU normalization, RSS aggregation, and network units through short tooltips plus always-visible labels where interpretation matters.

Use a native GTK list model and shared cell renderers rather than reconstructing per-cell widgets every tick. A 2,000-process native experiment found per-cell widget setup/update took 1.5–3.7 seconds. Shared `Gtk.TreeView` renderers plus cached text reduced the matched search/sort flow to about 105 ms p95. `TreeView` is supported by the target GTK 4.14 baseline but deprecated since 4.10; retain the behavior tests and revisit the renderer for a future GTK major-version migration. This changes the table implementation, not the specified interaction or data. Preserve scroll anchors, keyboard focus, expansion, and selection by identity. While a table has keyboard focus, hold row order stable; apply the selected sort again when focus leaves or the user explicitly re-sorts. Search and filters remain stable across updates. At wide sizes use a sidebar and multi-column charts; at 600×700 logical pixels collapse navigation and move secondary process fields into details. Validate a 1280×800 window and 200% scaling as well. Native accessible names, numeric text alternatives to charts, visible focus, dark/light appearance, and Escape dismissal are release requirements.

### 6. Keep runtime information local

No listener, analytics, remote fonts, update checks, account, cloud storage, or outbound runtime request. No packet payloads, command environments, or automatic disk recordings. Save only allowlisted UI preferences in the user's XDG config directory with atomic writes and restrictive permissions. Keep diagnostic logs bounded and free of process names, arguments, endpoint addresses, and raw snapshots by default. Invalid saved preferences fall back safely and visibly.

Root escalation, eBPF-based app bandwidth attribution, packet capture, end-task actions, startup management, and long-term recording require separately specified changes. A sandbox package is deferred because host process/sensor visibility needs a deliberate permission design; the first local launcher runs as the ordinary user.

### 7. Use measured release gates

These are acceptance targets, not verified results:

- First usable window within 2 seconds from a warm local launch; initial valid rates within two selected sampling intervals.
- With 500–600 processes, one-second updates, and the overview visible: ten-minute steady-state mean app CPU at most 1% of total machine capacity (equivalent to 20% of one logical CPU on a 20-logical-CPU host), RSS at most 200 MiB, and p95 system/process collection below 250 ms.
- At 2,000 fixture processes: p95 search/sort/navigation response within 200 ms, no input freeze exceeding 500 ms, and no unbounded queue/history growth. Fixture results do not prove live-system performance.
- After warming up, a 30-minute run has no sustained memory-growth trend above 10 MiB per ten minutes under a fixed workload and bounded histories. Report start/end RSS and intermediate observations rather than interpreting one fluctuation as a leak.

Measure startup, collection, GPU query, model/sort, and rendering separately, then report complete-app overhead. Benchmark the same workloads and visible views before and after any optimization. Do not change language or sampling accuracy based on the planning scan alone.

Tests must cover counter resets and gaps, process exit/PID reuse, denied individual fields, partial groups, missing sensors, NVML failure, interface/device disappearance, resume, preference corruption, and worker shutdown. Validate rates against synchronized raw-counter deltas, normalized CPU against a disposable single-thread workload, and GPU values against contemporaneous driver queries. Use temporary fixtures and local transfers; do not stress the GPU or restart active work for verification.

## Risks / Trade-offs

- Incomplete app identity metadata → expose the underlying process list and label uncertain membership rather than guessing.
- Restricted I/O and driver-specific metrics → availability per field and partial aggregate labels; no root prompt.
- Polling becomes expensive as process counts grow → measure by stage, batch cheap reads, restrict expensive details to the selected process, and enforce the full-app budget.
- Native GPU calls stall or fail → isolate the optional provider, cap in-flight work, mark stale data, retry with backoff, and keep the main loop responsive.
- Newer online examples exceed installed GTK/GI APIs → test against the observed versions and document the compatible baseline.
- Shared memory makes summed RSS look larger than real physical consumption → keep the RSS label and explanation visible; never reconcile it to system-used memory as if they were equivalent.
- Snapshot changes reorder rows during interaction → preserve identity and hold ordering while the table has focus.

## Migration Plan

Implement in the phases in [tasks.md](tasks.md). Run from the project environment first, then install a user-local desktop launcher with a stable command and clear icon/name. The launch/readback check must prove it opens the same application and shutting the window leaves no collector behind. Document startup, units, permissions, verification, and removal using Doc Agent.

No existing data or application migration is required. A failed local installation can be rolled back by removing only this app's launcher, project environment, and allowlisted preferences; preserve source and other applications. Repository creation, publication, issues, commits, pushes, PRs, and merges require authorization for their respective scope.

## Sources

Compatibility observations are local development evidence, not public-source claims. Online references were consulted for the proposed architecture; implementation must retain compatibility with the locally installed versions.

- [OpenSpec proposal workflow](https://github.com/Fission-AI/OpenSpec/blob/main/skills/openspec-propose/SKILL.md): planning artifacts and implementation boundary.
- [psutil API](https://psutil.readthedocs.io/stable/): metric definitions, CPU normalization, permissions, and counters. The online version is newer than the installed 5.9.8; do not assume new API names exist locally.
- [Linux /proc documentation](https://docs.kernel.org/filesystems/proc.html): process identity, memory accounting, and permission limitations.
- [PyGObject getting started](https://pygobject.gnome.org/getting_started.html) and [threading guide](https://pygobject.gnome.org/guide/threading.html): native runtime and GTK main-thread updates.
- [NVIDIA NVML reference](https://docs.nvidia.com/deploy/nvml-api/latest/index.html): optional GPU queries and supported-field handling.
- [libadwaita navigation](https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1.5/class.NavigationSplitView.html): adaptive sidebar/content navigation; verify each API against installed 1.5.
- [GTK TreeView API](https://docs.gtk.org/gtk4/class.TreeView.html): supported legacy cell-renderer API and deprecation boundary.
- [Rust/GTK](https://gtk-rs.org/gtk4-rs/stable/latest/book/introduction.html) and [Tauri prerequisites](https://v2.tauri.app/start/prerequisites/): alternative stack trade-offs.
