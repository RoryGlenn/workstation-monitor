# Proposal

## Why

Build a local Ubuntu task manager that makes it easy to see which apps consume resources and whether CPU, memory, GPU, storage, or networking is under pressure. A single, readable window should bring together app usage and hardware activity while explaining unavailable measurements honestly.

## What Changes

- Introduce **Workstation Monitor**, a native desktop application for an Ubuntu 24.04 GNOME desktop, inspired by Windows Task Manager's app list and performance views.
- Provide an overview, searchable and sortable app/process lists, process details, and live CPU, memory, NVIDIA GPU, disk, network, and available temperature graphs.
- Group related app processes where desktop metadata supports a reliable match; retain an explicit process view for everything else.
- Use one-second updates, five minutes of session history, consistent units, clear permission/unsupported/stale states, and controls to pause display updates or change the refresh interval.
- Run under the signed-in user's existing permissions, keep measurements in memory, and make no outbound requests. Save only interface preferences locally.
- Deliver a read-only first release focused on the user's request to see performance. Process termination, startup/service management, persistent recording, remote access, and per-app network bandwidth collection are separate future changes.

## Capabilities

### New Capabilities

- `application-monitoring`: App grouping, searchable process inventory, per-process measurements, identity, and partial-data handling.
- `hardware-monitoring`: CPU, RAM, swap, GPU, storage, and available hardware sensors with defined measurement semantics.
- `network-monitoring`: Per-interface traffic rates, counters, link state, and honest attribution boundaries.
- `monitoring-session`: Sampling, freshness, bounded history, performance budgets, privacy, settings, and collector lifecycle.
- `desktop-interface`: Overview and detail navigation, accessible live views, stable table interaction, adaptive layout, and desktop launch.

### Modified Capabilities

None. This is a new project with no existing implementation or specifications.

## Impact

- Planning and implementation live in this repository.
- Proposed stack: Python 3, GTK4/libadwaita through PyGObject, psutil, and NVIDIA's NVML through the `nvidia-ml-py` binding. Detailed alternatives and compatibility constraints are in [design.md](design.md).
- Reads Linux process/kernel counters and driver metrics; introduces no server, account, cloud service, root daemon, automatic startup, or changes to running workloads.
- The native runtime prerequisites and optional NVML Python binding are documented in the README. Launch and measurement flows must be verified on the target desktop.
- The proposal began as planning only. The subsequent implementation request is tracked in [tasks.md](tasks.md); delivered behavior and validation evidence are recorded in the [validation report](../../../docs/validation.md).
