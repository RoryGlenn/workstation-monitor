# Tasks

Checkboxes track implementation and verification; writing this file alone completes no task. Read [design.md](design.md) for the architecture and release budgets, [specs](specs) for the behavior contracts, and the [validation report](../../../docs/validation.md) for observed results.

## 1. Project foundation and native launch

- [x] 1.1 Create the minimal application package, development entry point, and project-local environment using compatible system GI libraries; verify that the entry point opens and closes a native window under the ordinary desktop user.
- [x] 1.2 Resolve the Cairo/GI bridge and record tested Python, GTK, libadwaita, psutil, and optional `nvidia-ml-py` dependencies; verify imports and one chart draw on the installed versions without replacing system Python or upgrading OS libraries implicitly.
- [x] 1.3 Add project guidance in AGENTS.md and a Doc Agent README with local setup, a launch command, expected first window, and dependency recovery steps; verify the documented launch from a fresh shell and keep future GitHub actions outside this task's authorization.

## 2. Snapshot model and session engine

- [x] 2.1 Implement measurement statuses, provider timestamps, process/device identity, and monotonic rate baselines; verify fixture tests for first sample, valid zero, reset, PID reuse, CPU topology change, and suspend/resume discontinuity.
- [x] 2.2 Implement the system sampler, isolated optional-provider worker, bounded latest-update handoff, and stale detection; verify failure/slow-provider fixtures leave unrelated metrics and main-loop interaction responsive with no accumulating callbacks or workers.
- [x] 2.3 Implement five-minute device buffers, current/previous process snapshots, and at most one selected-process history; verify time expiry and bounded retained sizes with long simulated sessions and process churn.
- [x] 2.4 Implement refresh intervals, Pause display semantics, hidden-window throttling, and clean shutdown; verify timing fixtures plus a native minimize/restore/close flow with no collector left running.
- [x] 2.5 Document sampling, pause, freshness, and unavailable states using Doc Agent; verify explanations match the implemented behavior and distinguish a zero measurement from missing data.

## 3. Linux hardware and network collection

- [x] 3.1 Collect normalized aggregate/per-core CPU, defined RAM/cache/available values, and swap; verify deterministic counter fixtures and compare a disposable single-thread workload and memory totals against synchronized local measurements.
- [x] 3.2 Discover physical storage devices and filesystems, calculate throughput/operations rates, and read available sensors; verify fixtures for partition/loop exclusion, device removal, unavailable sensors, and separate filesystem capacity, then compare live device counters without changing mounts.
- [x] 3.3 Discover physical/virtual/loopback network interfaces, link state/speed, and independent receive/send rates; verify counter-reset and reconnect fixtures plus a local transfer compared against matched interface-counter intervals, without adding a combined traffic total.
- [x] 3.4 Implement read-only NVIDIA device queries and supported process-VRAM lookup; verify failure/unsupported fixtures and contemporaneous driver readback for utilization, memory, temperature, and power without starting a GPU stress test or altering active jobs.
- [x] 3.5 Document units, CPU normalization, memory accounting, device throughput, sensor limits, and network attribution boundaries using Doc Agent; verify examples against live values and label unavailable capabilities explicitly.

## 4. Process inventory and app grouping

- [x] 4.1 Collect process identity, owner/state, CPU/RSS, parent/threads, and readable storage I/O with independent field failures; verify denied-I/O fixtures preserve other fields and live inventory retains restricted processes without requesting root.
- [x] 4.2 Resolve supported desktop IDs and app-scope metadata into groups with a process fallback; verify multiprocess app fixtures, same-name unrelated processes, distinct application boundaries, unmatched processes, and no duplicate membership.
- [x] 4.3 Implement group CPU/RSS/I/O totals and read-only selected-process details; verify partial totals, shared-RSS labels, exits/PID reuse, and unsupported process-VRAM states, with no default command-line/environment collection.
- [x] 4.4 Document app grouping, fallback coverage, process memory, partial values, and read-only scope using Doc Agent; verify each explanation against the corresponding fixture and at least one real desktop app group when metadata permits.

## 5. Native interface and live interaction

- [x] 5.1 Build Overview, Apps, Processes, and Performance navigation with overview-to-detail links; verify the real flow from a busy resource/app summary to its matching detail and back while live data updates.
- [x] 5.2 Add recycled table rows, search, numeric sorting, owner filtering, expansion, and identity-based selection; verify focus/scroll stability during refresh, explicit re-sort behavior, and exit handling with changing fixture values and the live inventory.
- [x] 5.3 Add labeled charts, gaps, last-update states, fixed percentage scales, throughput scales, and text alternatives; verify rendering fixtures for missing intervals and inspect the actual native charts for readable units and scale changes.
- [x] 5.4 Add Pause display, interval settings, visible state explanations, concise accessible tooltips, and keyboard navigation; verify mouse and keyboard flows, Escape dismissal, focus order, and state comprehension without relying on hover or color.
- [x] 5.5 Implement adaptive navigation and detail layouts; verify 1280×800 and 600×700 logical-pixel windows, 200% scaling, and light/dark appearance with screenshots and an actual usability check for essential controls and labels.
- [x] 5.6 Update the Doc Agent user guide for navigation, charts, filtering, and settings; verify every documented control against the running interface and label the screenshots' actual layout/version.

## 6. Local settings and desktop delivery

- [x] 6.1 Persist only allowlisted interface preferences with atomic user-local writes and restrictive permissions; verify restart readback, corrupt-file recovery, unsupported values, and absence of process measurements/names in saved preferences.
- [x] 6.2 Keep default diagnostics bounded and sanitized; verify fixtures cannot log process names, arguments, environment values, endpoint addresses, or raw snapshots and that routine operation creates no history recording.
- [x] 6.3 Add a user-local Workstation Monitor launcher and documented removal path; verify launching from the desktop application menu opens the expected app as the current user and closing leaves no worker or autostart entry.
- [x] 6.4 Document install, launch, permissions, troubleshooting, and removal using Doc Agent; verify the exact startup steps from a fresh shell and inspect installed launcher/config paths without removing unrelated files.

## 7. End-to-end acceptance and performance

- [x] 7.1 Run the complete real flow: desktop launch → Overview → search/sort app → inspect process → GPU/disk/network details → pause/resume → narrow layout → restart preference readback → close; verify local measurements, stable interaction, and no remaining collector, recording concrete outcomes rather than clicks alone.
- [x] 7.2 Measure warm startup and ten-minute complete-app CPU/RSS with 500–600 processes and one-second overview updates; record collection/GPU/model/render stages separately, compare against design budgets, and verify any optimization with the same workload and output accuracy before adoption.
- [x] 7.3 Run the 2,000-process fixture interaction benchmark and 30-minute live retention soak; verify latency, memory trend, and bounded queues/history against the specifications and report fixture versus live evidence separately.
- [x] 7.4 Exercise provider failures, denied fields, corrupt settings, device/interface replacement, suspend/resume, and offline runtime as an integrated app; verify graceful states, continued navigation, no network listeners/outbound attempts, and clean exit using scoped fixtures/instrumentation without changing workstation-wide networking.
- [x] 7.5 Review the final source/documentation diff and capability coverage, run project checks and strict OpenSpec validation, and record evidence in a Doc Agent validation note; verify every requirement has a test or explicit live check and report unresolved budgets or capability gaps before calling the app complete.
