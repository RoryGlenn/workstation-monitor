# Use Workstation Monitor

## Find what is busy

Start with **Overview**. Its wide CPU timeline shows up to five minutes of whole-machine activity. The panels below show memory, GPU utilization, filesystem capacity/free space, temperatures, and both network directions for the named interface. Select a resource panel to see related measurements in **Performance**. The CPU temperature opens **Sensors**; the GPU temperature opens **GPU**.

The three busiest apps appear in aligned **App**, **CPU**, and **Memory (RSS)** columns. Choose **Highest CPU** or **Highest memory**, select a row to inspect its details, or choose **View all apps** for the full list. Row identity stays stable while a row has keyboard focus. **Apps** groups processes only where desktop identity metadata supports the relationship. Other processes remain individually accessible. Matching executable names alone do not create a group. A group name can appear more than once when separate desktop scopes identify separate launches.

Use **Processes** for the full visible inventory. Search by name or PID, choose a numeric sort, or enable **My processes**. Select a row and press Enter, or select **View details**. In Apps, the arrow expands member processes. Ctrl+F focuses the search box. Escape closes detail and settings windows.

Values update while you read. The table holds row order while it has keyboard focus; choose a sort again or leave the table to apply the current ranking. Selection and expansion follow process identity, so a reused PID does not become the process you were inspecting.

## Pause and refresh

**Pause display** freezes visible values and shows their snapshot time. Collection continues in memory. **Resume display** jumps to current data rather than replaying old updates.

Open **Settings** with the gear button to choose a 1-, 2-, or 5-second interval and System, Light, or Dark appearance. New installations use the graphite Dark appearance; previously saved choices are respected. **Save settings** persists only these preferences. Minimized or hidden windows collect no faster than every five seconds. Closing the app stops collection.

At narrow widths, the icon-and-label sidebar becomes a destination selector and Overview's panels form one column. Scroll vertically to reach the remaining summaries and app rows. Secondary process columns move into details. Graphs have numeric values and units so color is not the only way to understand them.

## Read the measurements correctly

| Value | Meaning |
| --- | --- |
| CPU % | Percentage of the entire machine's capacity. For example, on a 20-logical-CPU host, one fully occupied logical CPU is about 5%. |
| RAM used | OS-usable total minus available RAM. Cache and swap are shown separately; cache is not assigned to an app. |
| Memory · RSS | Process resident memory. Summed group RSS can count shared pages more than once and need not add up to system-used RAM. |
| GPU | The large percentage and bar show device utilization; the labeled VRAM used/total is a separate reading. Temperature (°C) and power (W) are available in GPU details. Process VRAM is shown only where the driver supports attribution. |
| Storage | Overview shows the root filesystem's used percentage and free bytes, or a clearly named local filesystem when root is absent. An unreadable root remains unavailable. The capacity bar turns amber at 90% used. Performance shows physical-drive read/write rates and operations separately; partition traffic is not added again. Process disk values are kernel-accounted storage I/O, not every file operation. |
| Network | Receive/send throughput for the selected interface in KiB/s or MiB/s. Reported link capacity uses Mbit/s. This is not an internet speed test or per-app bandwidth measurement. |
| Sensors | Named readings actually reported by hardware. Overview's CPU temperature uses an identifiable CPU package/core sensor; it never substitutes a drive or ACPI reading. GPU temperature comes from the same GPU as its utilization. Missing fan speed or temperature is not inferred. |

Byte sizes use B, KiB, MiB, GiB, and TiB. Graphs cover up to five minutes from this session. CPU/percentage scales stay at 0–100%; other scales adapt and show their units and upper value. Network receive uses a solid mint line and send a dashed blue line, with separate labeled numbers; they share one scale. Missing intervals remain gaps. No session history is saved to disk. Only the currently inspected process can retain a recent detail history.

## Understand missing data

| State | What to do |
| --- | --- |
| Measuring… | Wait for the next valid sample. A counter reset, new device, CPU-count change, or resume can require a fresh baseline. |
| Permission denied | The current user cannot read that field. Other values stay visible; the app does not request root access. |
| Unsupported | The provider or driver does not support that measurement. |
| Unavailable | The source could not return a measurement. Other providers continue working. A failed system sample leaves process counts/current app values unavailable; it does not establish an exit. Retained detail values show their last successful observation time. |
| Stale | Two scheduled intervals were missed. Last-good values are marked with their last successful update time. |
| Partial | A group subtotal excludes unreadable member values. It is not a complete app total. |
| Disconnected / Exited | The device or process is gone; old counters are not followed as a replacement's measurements. |

A real zero requires two valid counter samples. Unknown, warming, denied, and missing values are never replaced by zero.

## Troubleshoot

**The window does not open:** run `./run.sh` from a terminal in the project folder. It requires your graphical desktop session, not an SSH-only session. If imports fail, run `sh scripts/setup.sh`; the compatible Ubuntu native packages listed in the README must already be present. Setup does not install system packages or ask for administrator credentials.

**GPU is unavailable:** verify that `nvidia-smi` can query your installed driver. Setup installs the optional Python binding; unsupported GPU/driver fields remain unavailable while other views work. No GPU workload needs restarting.

**Network totals differ from another tool:** check the selected interface and sampling interval. Loopback and virtual bridges are separate from physical adapters. The same transfer can cross multiple interfaces; their counters are not summed into a single total.

**Link state or speed is unknown:** a restrictive process policy can block the local ioctl socket used for link metadata. Readable interface counters and other system measurements continue; unknown link metadata is not treated as a disconnected device.

**Preferences reset:** invalid or unsupported preferences trigger safe defaults and a visible notice. Settings live in `~/.config/workstation-monitor/preferences.json` unless XDG_CONFIG_HOME or the test-only WORKSTATION_MONITOR_CONFIG_DIR overrides the location. No process names or history belong in that file.

**Values differ from another monitor:** match its sampling period and accounting first. Whole-machine CPU, reclaimable cache, summed RSS, and physical-drive I/O each have distinct definitions; different definitions can produce different valid numbers.
