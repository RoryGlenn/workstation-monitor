# Application Monitoring Spec Delta

## Purpose

Help the user identify which applications and processes consume resources while preserving process identity and making incomplete measurements clear.

## ADDED Requirements

### Requirement: Searchable process inventory
The application SHALL list running processes visible to the current user, with name, PID, owner, state, CPU percentage, resident memory, and storage read/write rates where available. It SHALL support name/PID search, numeric sorting, and an owner filter without requiring elevated permissions.

#### Scenario: Find a process while values update
- **WHEN** the user searches for a process name or PID and sorts by CPU usage
- **THEN** matching rows remain filtered across refreshes and numerical values determine the sort
- **AND** the selected process remains selected by its identity

### Requirement: Reliable application grouping
The application SHALL provide app groups when desktop identity metadata supports the association, with expandable process members. Each process SHALL belong to at most one group. Unmatched processes SHALL remain accessible in the process inventory; identical names alone SHALL NOT establish a group.

#### Scenario: Application with child processes
- **WHEN** desktop metadata reliably associates multiple processes with one application
- **THEN** the app view shows one expandable group containing those processes and their aggregated measurements

#### Scenario: Ambiguous association
- **WHEN** two unrelated processes have the same executable name without shared application identity evidence
- **THEN** the application does not merge them solely on that name and both remain accessible individually

### Requirement: Honest application totals
The application SHALL aggregate member CPU, resident memory, and readable storage I/O without counting a process twice. It SHALL label incomplete aggregates as partial. Summed resident memory SHALL be labeled RSS and explain that shared pages can be counted more than once.

#### Scenario: Partially readable app group
- **WHEN** one group member's storage I/O is permission denied and other members report valid counters
- **THEN** the group shows the readable subtotal with a partial-data label
- **AND** it retains the inaccessible member and does not present the subtotal as the complete app total

### Requirement: Field-level measurement availability
The application SHALL preserve readable fields when another field is denied, unsupported, or unavailable, and SHALL explain the affected field's state without substituting zero or removing the process row.

#### Scenario: Restricted process I/O
- **WHEN** process name, CPU, and memory are readable but storage I/O counters are denied
- **THEN** name, CPU, and memory remain visible and the I/O fields indicate permission denied
- **AND** no elevation prompt appears

### Requirement: Stable process identity
The application SHALL distinguish processes using PID and start identity within the current boot. Exited processes SHALL stop receiving updates, and a reused PID SHALL NOT inherit the prior process's details, measurements, or selection.

#### Scenario: Process exits and PID is reused
- **WHEN** a selected process exits and a different process later receives the same PID
- **THEN** the old detail view indicates that its process has exited
- **AND** the replacement is treated as a new process with fresh rate baselines

### Requirement: Read-only process details
The application SHALL expose selected-process identity, owner, parent, thread count, start time, resource values, and supported GPU memory attribution without changing the process. It SHALL NOT collect full command-line arguments or environment variables by default, or offer process termination in this release.

#### Scenario: Inspect an active workload
- **WHEN** the user opens details for a running process
- **THEN** the available identity and performance values appear with field-level availability labels
- **AND** inspecting or closing the detail view does not signal, restart, reprioritize, or otherwise modify that workload

#### Scenario: Driver cannot attribute process GPU memory
- **WHEN** GPU device metrics are available but the driver cannot report memory for the selected process
- **THEN** process GPU memory is explicitly unavailable or unsupported rather than inferred from the device total
