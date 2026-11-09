# Desktop Interface Spec Delta

## Purpose

Provide a clear native desktop interface that connects an overview of resource activity to inspectable application, process, and hardware details.

## ADDED Requirements

### Requirement: Overview and detail navigation
The application SHALL provide Overview, Apps, Processes, and Performance destinations with clear everyday labels. Overview SHALL link CPU, memory, GPU, storage, and selected-interface summaries to the relevant detail view and link high-usage apps to their members or details.

#### Scenario: Investigate high memory usage
- **WHEN** the user selects a high-memory app from Overview
- **THEN** the app's grouped members or details open with memory values and their measurement labels
- **AND** the user can return to Overview without losing navigation context

### Requirement: Stable live interaction
The application SHALL preserve scroll anchors, focus, expanded app groups, and selection by identity during updates. A table SHALL hold row order while it has keyboard focus and apply its selected sort when focus leaves or the user explicitly re-sorts.

#### Scenario: CPU ranking changes while inspecting a row
- **WHEN** CPU values change while the table has keyboard focus and a row is selected
- **THEN** values update without moving the focused row or resetting the scroll position
- **AND** an explicit re-sort applies the chosen ranking while preserving selection identity

### Requirement: Adaptive desktop layout
The application SHALL remain usable at 1280×800 and 600×700 logical pixels and at 200% display scaling. Narrow windows SHALL collapse navigation and move secondary process fields into details while preserving essential values and controls.

#### Scenario: Resize to a narrow window
- **WHEN** the app is resized from a wide layout to 600×700 logical pixels
- **THEN** navigation, app search, primary metrics, pause, and refresh controls remain reachable
- **AND** secondary fields remain available in details without clipped essential labels

### Requirement: Accessible controls and measurements
The application SHALL provide visible keyboard focus, accessible names, keyboard navigation, Escape dismissal for transient views, light/dark appearance, and textual values alongside charts. Status and resource meaning SHALL NOT depend on color alone.

#### Scenario: Inspect using the keyboard
- **WHEN** the user navigates to a process and opens its details using only the keyboard
- **THEN** focus remains visible, measurements have readable text, and Escape dismisses the transient view predictably

### Requirement: Visible measurement explanations
The application SHALL label units, paused/stale/partial states, and unavailable measurements clearly. Concise tooltips SHALL explain CPU normalization and RSS aggregation; essential state and interpretation SHALL remain available outside tooltips.

#### Scenario: Inspect a partial RSS total
- **WHEN** the user views a group with partial measurements and summed resident memory
- **THEN** the partial state and RSS label are visible without hovering
- **AND** a keyboard-accessible explanation describes shared-page counting

### Requirement: User-local desktop launch
The application SHALL provide a documented project launch command and a user-local desktop launcher named Workstation Monitor. Launching SHALL require no administrator authentication or cloud access, and SHALL NOT enable automatic startup.

#### Scenario: Launch from the application menu
- **WHEN** the user activates the installed Workstation Monitor launcher
- **THEN** the native monitoring window opens and produces live local measurements
- **AND** closing it leaves no background collector and does not change startup settings
