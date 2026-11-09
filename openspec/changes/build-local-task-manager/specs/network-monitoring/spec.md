# Network Monitoring Spec Delta

## Purpose

Show network interface activity and link state without confusing local throughput, link capacity, internet speed, or application-level attribution.

## ADDED Requirements

### Requirement: Per-interface network activity
The application SHALL display each discovered interface's identity, link state, receive/send rates, cumulative counters, and reported link speed when available. Byte rates SHALL use KiB/s or MiB/s; link capacity SHALL be separately labeled Mbit/s and unknown values SHALL remain unknown.

#### Scenario: Active Ethernet link
- **WHEN** two valid counter samples arrive for an active Ethernet interface
- **THEN** receive and send rates are calculated independently over the actual elapsed interval
- **AND** reported link speed is distinguishable from current throughput

#### Scenario: Unknown Wi-Fi capacity
- **WHEN** an active Wi-Fi interface has traffic counters but no reliable link-speed measurement
- **THEN** its traffic rates remain available and its link speed is labeled unknown

### Requirement: Physical and virtual interface distinction
The application SHALL distinguish physical, virtual, and loopback interfaces, permit their individual selection, and avoid presenting the sum of all interfaces as total traffic. Overview traffic SHALL identify the selected interface.

#### Scenario: Traffic crosses a bridge and physical adapter
- **WHEN** the same transfer contributes counters on a virtual bridge and a physical adapter
- **THEN** both remain individually inspectable and the overview identifies which one it shows
- **AND** it does not add those counters into an unexplained combined total

### Requirement: Interface lifecycle handling
The application SHALL discover new interfaces and mark disappeared interfaces disconnected. Renamed, replaced, or reset interfaces SHALL receive fresh rate baselines instead of inheriting another interface's history or producing negative rates.

#### Scenario: Adapter reconnects with reset counters
- **WHEN** a selected adapter disconnects and returns with lower counters or a new identity
- **THEN** the view identifies the transition and shows a measuring state until a valid new interval exists
- **AND** it does not publish a negative rate or an artificial traffic spike

### Requirement: Attribution boundary
The application SHALL label these measurements as interface throughput. It SHALL NOT claim to measure internet speed, assign interface totals to individual applications, collect packet payloads, or require packet-capture/elevated privileges in this release.

#### Scenario: User inspects app network activity
- **WHEN** the user inspects an app while interface throughput is available
- **THEN** no per-app bandwidth value is inferred from interface totals
- **AND** the interface view explains that app bandwidth attribution is outside this release

### Requirement: Network history and availability
The application SHALL show receive/send history with timestamps, visible scales, and separate directions. Missing or restricted measurements SHALL retain their availability state and appear as gaps rather than measured zero traffic.

#### Scenario: Valid idle link versus missing reading
- **WHEN** an interface has unchanged counters over a valid interval followed by a failed counter read
- **THEN** the valid interval shows zero throughput and the failed interval shows unavailable data
- **AND** the graph preserves the distinction
