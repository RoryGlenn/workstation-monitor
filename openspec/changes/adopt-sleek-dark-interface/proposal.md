# Proposal

## Why

The user selected the sleek dark mockup for implementation. The current Overview gives every resource the same small graph and displays busy apps as unaligned text buttons; filesystem free space, upload traffic, and temperatures require opening other views.

## What Changes

- Adopt graphite surfaces, mint graph traces, subtle borders, icon navigation, a clear page heading, and visible live/paused states throughout the native app.
- Make a wide CPU history the Overview anchor. Arrange memory, GPU, filesystem capacity, CPU/GPU temperatures, and bidirectional interface traffic beneath it.
- Present the three busiest apps in aligned App / CPU / Memory (RSS) rows with details and a route to the full Apps view.
- Reflow the dashboard at narrow widths and preserve keyboard access, unavailable/partial/stale states, pause semantics, light/system appearance choices, and the existing detailed views.
- Default new installations to Dark while respecting previously saved choices. Use actual measurements and labels rather than the mockup's fictional numbers.

## Capabilities

### New Capabilities

- `overview-dashboard`: A focused resource dashboard with coherent theme, honest capacity/temperature/network summaries, accessible navigation, and adaptive layout. The capability inventory is currently empty; the earlier completed, unarchived `build-local-task-manager` change supplies the existing interface contracts that this change must preserve.

### Modified Capabilities

None in the canonical capability inventory.

## Impact

Native presentation, default appearance, focused dashboard selection helpers, native integration checks, and user documentation. Existing Linux/NVML collectors, worker scheduling, privacy boundaries, measurement definitions, and launcher remain in place. No added runtime dependency, network service, account, or process-control action. Local mockups, screenshots, and raw benchmark files remain ignored. The user's follow-up authorizes final review and pushing the reviewed source changes.
