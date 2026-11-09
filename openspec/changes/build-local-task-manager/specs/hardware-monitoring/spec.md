# Hardware Monitoring Spec Delta

## Purpose

Show current hardware resource usage with consistent units, defined accounting, and clear boundaries between measured, missing, and unsupported values.

## ADDED Requirements

### Requirement: Consistent CPU scale
The application SHALL show aggregate and per-logical-CPU utilization on a 0–100% scale. Process and app CPU percentages SHALL use whole-machine capacity, with an explanation of normalization and a new baseline when the online CPU count changes.

#### Scenario: One busy logical CPU
- **WHEN** one process consumes approximately one logical CPU over a valid interval on a machine with 20 online logical CPUs
- **THEN** its CPU usage is approximately 5% of whole-machine capacity
- **AND** the scale explanation is available from the CPU label

### Requirement: Defined memory accounting
The application SHALL display OS-usable total, available, used, cache, and swap memory using IEC byte units. Headline used RAM SHALL equal total minus available. App RSS totals SHALL remain distinct from system used memory.

#### Scenario: Cache is reclaimable
- **WHEN** the operating system reports memory in cache and a valid available-memory value
- **THEN** headline used RAM uses total minus available and cache is shown separately
- **AND** the application does not attribute that cache to an individual app

### Requirement: NVIDIA device monitoring
The application SHALL display reported NVIDIA device utilization, VRAM used/total, temperature, and power with separate units and availability states. Failure or absence of GPU support SHALL NOT prevent CPU, memory, disk, or network monitoring.

#### Scenario: Supported NVIDIA device
- **WHEN** the installed driver reports valid device metrics
- **THEN** GPU utilization is labeled percent, VRAM uses IEC byte units, temperature uses degrees Celsius, and power uses watts
- **AND** GPU utilization and VRAM consumption are presented as separate measurements

#### Scenario: GPU provider fails
- **WHEN** the GPU provider cannot initialize, stops responding, or rejects a metric
- **THEN** affected GPU values indicate the appropriate unavailable, stale, or unsupported state
- **AND** other hardware values continue updating

### Requirement: Storage usage and throughput
The application SHALL distinguish physical-device read/write throughput and operations per second from filesystem capacity. Device totals SHALL NOT double count a physical device and its partitions, or treat snapshot/Snap loop devices as additional physical drives.

#### Scenario: Device with several partitions
- **WHEN** a physical drive and its partitions report I/O counters
- **THEN** its device throughput uses the physical-device counters once
- **AND** filesystem used/available capacity is shown separately with its filesystem identity

#### Scenario: Drive disappears
- **WHEN** a previously monitored removable drive is no longer present
- **THEN** its view marks the device disconnected and stops deriving rates from the old counters

### Requirement: Reported sensors only
The application SHALL display available temperature and other supported hardware sensor readings with names and units. Missing, restricted, or unsupported sensors SHALL NOT be displayed as zero or inferred from unrelated devices.

#### Scenario: Temperature without fan information
- **WHEN** CPU temperature is reported but fan speed is unavailable
- **THEN** CPU temperature appears with its sensor label and units
- **AND** fan speed is omitted or explicitly unavailable rather than invented

### Requirement: Honest hardware history
The application SHALL provide timestamped recent graphs for monitored hardware, with percentage axes fixed at 0–100% and visible units for byte rates and quantities. Throughput autoscaling SHALL expose the current scale. Missing measurements SHALL appear as gaps.

#### Scenario: Missing sample during a throughput spike
- **WHEN** one interval is unavailable between two valid disk-throughput measurements
- **THEN** the graph preserves the missing interval as a gap and labels any changed throughput scale
- **AND** it does not substitute a zero sample or connect the gap as uninterrupted measured data
