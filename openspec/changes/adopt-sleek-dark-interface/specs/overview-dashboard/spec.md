# Overview Dashboard Spec Delta

## Purpose

Give users an immediately readable view of resource activity, available storage, and busy applications in a coherent native desktop dashboard.

## ADDED Requirements

### Requirement: Graphite visual hierarchy
The dashboard SHALL present graphite surfaces, mint data accents, restrained borders, icon-and-label navigation, a clear page heading, and readable numeric columns. New installations SHALL default to Dark; saved System, Light, and Dark choices SHALL remain supported.

#### Scenario: Open the redesigned application
- **WHEN** the user launches with no saved preferences
- **THEN** Overview opens in the sleek dark appearance with working Overview, Apps, Processes, and Performance navigation
- **AND** choosing Light or System remains available in Settings

### Requirement: Resource overview
Overview SHALL emphasize a wide five-minute CPU history and display memory, GPU utilization with separately labeled VRAM, named filesystem capacity/free space, CPU/GPU temperatures, and selected-interface receive/send rates. Resource summaries SHALL open their corresponding Performance destination.

#### Scenario: Inspect storage capacity
- **WHEN** a readable root filesystem exists
- **THEN** Storage shows its used percentage, available bytes, and mount identity instead of substituting a physical-device transfer rate
- **AND** activating Storage opens the detailed storage view

#### Scenario: Inspect both traffic directions
- **WHEN** a selected network interface has valid receive and send samples
- **THEN** both rates and their units appear alongside a shared history graph and interface name
- **AND** changing the interface in Performance updates Overview's selection

### Requirement: Honest measurement states
Summaries SHALL distinguish utilization, capacity, and temperature, retain readable fields when optional fields fail, and visibly label unavailable, measuring, partial, paused, and stale values. Percentage charts SHALL use 0–100%; throughput charts SHALL show their scale and preserve missing intervals as gaps.

#### Scenario: Optional readings are absent
- **WHEN** GPU memory or an identifiable CPU temperature is unavailable
- **THEN** the affected field shows its unavailable state while valid utilization, memory, process, and network values remain usable
- **AND** no missing number appears as a measured zero or as an unrelated sensor's temperature

#### Scenario: Freeze the display
- **WHEN** the user selects Pause display
- **THEN** values, histories, status, and timestamps describe the frozen snapshot across navigation
- **AND** a visible banner explains that collection continues until Resume display or close

#### Scenario: System sampling fails
- **WHEN** system sampling cannot produce a valid inventory
- **THEN** process counts and current app values are labeled unavailable rather than zero or exited
- **AND** details identify retained values with their last successful observation time until a valid inventory can confirm an exit or recovery

#### Scenario: Inspect a retained member after exit
- **WHEN** the user opens a retained app row or its member after that identity has exited
- **THEN** details use that identity's last observed values and observation time together
- **AND** the member action does not reuse older values captured when its button was created

### Requirement: Busy app table
Overview SHALL show three ranked app/group rows with App, CPU, and Memory (RSS) columns, Highest CPU/Highest memory ranking, accessible row actions, and a View all apps action. Partial CPU/RSS subtotals SHALL be labeled. Focused app rows SHALL not silently become another app during live ranking updates.

#### Scenario: Inspect a busy app using the keyboard
- **WHEN** a resource row has keyboard focus while CPU rankings change
- **THEN** the row keeps its app identity and values continue updating
- **AND** activating it opens the matching details, Escape closes details, and View all apps opens Apps

### Requirement: Adaptive and bounded presentation
The dashboard SHALL remain usable at 1280×800 and 600×700 logical pixels and 200% scaling. Narrow layouts SHALL collapse navigation and stack panels without horizontal clipping. Essential controls and all summaries SHALL remain reachable, and live updates SHALL preserve the reading position and existing worker/history bounds.

#### Scenario: Read Overview in a narrow window
- **WHEN** the window becomes 600×700 logical pixels
- **THEN** destination selection, pause, settings, and readable summary values remain available
- **AND** vertical scrolling reaches the network, temperature, storage, and app panels without horizontal scrolling
