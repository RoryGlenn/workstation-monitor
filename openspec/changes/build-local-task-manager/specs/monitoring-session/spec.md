# Monitoring Session Spec Delta

## Purpose

Keep live monitoring responsive, bounded, private, and understandable across refresh changes, missing samples, interrupted providers, and application shutdown.

## ADDED Requirements

### Requirement: Refresh and display pause controls
The application SHALL default to one-second sampling, offer 1-, 2-, and 5-second intervals, and provide a separately labeled Pause display control. Pausing SHALL freeze the visible snapshot while collection continues, show a paused banner with snapshot time, and resume to the latest measurements.

#### Scenario: Inspect a paused snapshot
- **WHEN** the user activates Pause display and later resumes
- **THEN** values stay frozen with a visible paused indication until resume
- **AND** collection continues while paused and resume presents current values without replaying queued frames

### Requirement: Valid rate baselines
The application SHALL derive rates from valid counter differences and actual monotonic elapsed time. First samples, counter decreases, identity changes, and suspend/resume discontinuities SHALL invalidate the prior baseline and display Measuring until a new valid interval is available.

#### Scenario: Refresh interval changes
- **WHEN** the interval changes from one second to five seconds during valid collection
- **THEN** the next rate uses its actual elapsed duration rather than assuming one second

#### Scenario: Counter reset
- **WHEN** a counter decreases or collection resumes after a suspend discontinuity
- **THEN** no negative rate or artificial spike appears and the affected measurement receives a new baseline

### Requirement: Independent provider freshness
The application SHALL track successful-update times per provider, distinguish unavailable, unsupported, denied, warming, and stale values, and mark a provider stale after two missed scheduled intervals. A stalled optional provider SHALL NOT stop other providers or user interaction.

#### Scenario: GPU stops responding
- **WHEN** CPU/network collection succeeds but GPU updates miss two scheduled intervals
- **THEN** GPU values show stale status and their last successful update time
- **AND** CPU/network views and navigation continue updating and responding

### Requirement: Bounded session retention
The application SHALL retain at most five minutes of device/overview graph history, current/previous process snapshots, and recent history for at most one selected process. It SHALL NOT retain histories for every process or persist measurement history to disk in this release.

#### Scenario: Many processes over a long session
- **WHEN** the application runs for more than five minutes and the user inspects several processes in sequence
- **THEN** device history ages out and only the current selected process retains a detail history
- **AND** retained measurements and pending presentation updates remain bounded

### Requirement: Hidden-window and shutdown lifecycle
The application SHALL stop repainting and sample no faster than every five seconds when its window is not visible. Closing the app SHALL stop collectors and timers, release GPU resources where possible, and leave no background monitoring service or orphan worker.

#### Scenario: Minimize then close
- **WHEN** the user minimizes the app, restores it, and then closes it
- **THEN** minimized sampling respects the reduced frequency, restored sampling returns to the selected interval, and closing leaves no monitoring worker behind

### Requirement: Local runtime privacy
The application SHALL operate without accounts, outbound requests, network listeners, analytics, root privileges, packet payload collection, or automatic recording. Default diagnostics SHALL exclude process names, command arguments, environment values, endpoint addresses, and raw measurement snapshots.

#### Scenario: Monitor while offline
- **WHEN** the app runs with outbound networking blocked
- **THEN** local monitoring remains functional and the app attempts no outbound connections or remote resource loads

### Requirement: Safe preference persistence
The application SHALL persist only allowlisted interface preferences in user-local configuration with restrictive permissions and atomic writes. Corrupt or unsupported preferences SHALL use safe defaults with a visible explanation and SHALL NOT prevent launch.

#### Scenario: Restore preferences after restart
- **WHEN** the user changes refresh interval or appearance and restarts the app
- **THEN** valid preferences are restored without restoring process names or measurement history

#### Scenario: Corrupt preferences
- **WHEN** the saved preference file is invalid
- **THEN** the app opens using safe defaults and explains that preferences could not be loaded

### Requirement: Measurable live performance budget
The application SHALL meet a warm-launch usable-window target of 2 seconds and, with 500–600 live processes, a visible overview, and one-second sampling, a ten-minute mean CPU budget of 1% of total machine capacity, RSS of at most 200 MiB, and p95 system/process collection below 250 ms on the target workstation.

#### Scenario: Live acceptance benchmark
- **WHEN** the app is benchmarked with the specified workload after warm-up
- **THEN** startup, complete-app CPU/RSS, and collection timings are recorded separately against these budgets
- **AND** the release is not reported as meeting them when a required budget fails

### Requirement: Responsive and bounded long sessions
The application SHALL achieve p95 search/sort/navigation latency within 200 ms and no input freeze above 500 ms with 2,000 fixture processes. A fixed-workload 30-minute run after warm-up SHALL show no sustained RSS growth above 10 MiB per ten minutes and no unbounded queue or history growth.

#### Scenario: Stress inventory and session retention
- **WHEN** the fixture workload exercises search, sorting, and navigation, and a separate live soak exercises retention
- **THEN** interaction latency, intermediate RSS observations, and retained sizes are recorded against the budgets
- **AND** fixture performance is distinguished from live-system performance
