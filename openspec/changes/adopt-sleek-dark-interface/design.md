# Design

## Context

See [proposal.md](proposal.md) for the selected direction. The reference is the user's locally saved sleek dark mockup; it is a visual guide, not a source of runtime readings. GTK 4.14/libadwaita 1.5, shared process-table renderers, two bounded collection workers, and snapshot history are already implemented. Existing contracts in `build-local-task-manager` remain applicable.

The current UI has five identical chart cards and free-form app buttons. Filesystem capacity and temperatures already arrive in the system frame, and NVIDIA utilization, memory, and temperature arrive independently. This is a presentation change; no new polling or provider APIs are needed.

## Goals / Non-Goals

**Goals:** Reproduce the selected design's hierarchy and palette with native widgets, improve immediate usefulness, preserve truthful measurements and existing detail flows, and retain a light/system option.

**Non-Goals:** Pixel-copying fictional readings, replacing GTK with a web stack, collecting new private fields, modifying workloads, adding process-control actions, or claiming a renewed long-duration performance certification from a short comparison.

## Decisions

### Native reusable presentation

Use a small theme stylesheet and native panels/buttons/labels for summaries and app rows. Retain the existing efficient Apps/Processes tables. A large CPU chart spans the dashboard; a three-column grid below has memory/GPU above storage/temperatures and a two-row network panel. A compact three-row app table follows. Below the navigation breakpoint, place the same widgets in one column. Prefer widget reparenting only on a layout change over rebuilding at every sample.

Keep the reference's dark graphite/mint palette; supply equivalent light colors for the existing explicit appearance preference. New defaults become Dark, while saved preferences are not migrated or overwritten. Theme changes also apply to details/settings and graphs. Use native symbolic icons and keyboard-focus indicators instead of new images, external fonts, or dependencies.

### Snapshot-derived summaries

Select root filesystem capacity when present; otherwise label the first available local filesystem explicitly. Preserve a failed root reading instead of silently replacing it with another mount. Use reported percentage/free values and clear units. CPU temperature uses identifiable CPU-package/core sensor metadata (for example coretemp Package or k10temp Tdie/Tctl); never substitute ACPI or storage temperatures. GPU utilization, VRAM fraction, and temperature remain separate fields from the same GPU identity. Network upload/download share a labeled scale and distinct line styles/colors plus text legends.

Compute presentation choices in small pure helpers with focused failure/identity tests. Do not change collectors or session retention. Stale/paused state must reach every new field and the header/footer; the frame freshness remains authoritative even if a capacity value is cached by its existing provider.

### Accessible stable interactions

Keep Pause display and Settings separate, show the pause banner and update state outside tooltips, and expose numeric text for graphs/bars. Use native row buttons with App/CPU/Memory (RSS) alignment and names; hold app identity/order while those rows have keyboard focus. Keep resource-to-detail navigation, sort selection, and process inventory behavior. Freeze histories and values from the same existing snapshot when paused.

### Verification and performance

Capture a short real-native baseline before runtime edits, then repeat the same duration, refresh interval, window size, renderer, and host workload with the final code. Report complete-process CPU/RSS separately from collector, model, drawing, and main-thread timings. The previous long soak remains historical evidence only. Include stylesheets in benchmark source hashing and avoid treating fixture throughput as live overhead.

Extend the native flow for dashboard navigation, source selection, unknown/stale/partial fields, keyboard-focus stability, and pause consistency. Inspect real GTK captures at desktop/narrow sizes, light/dark, and 200% scaling. Continue existing counter/provider, offline, faulty-provider, startup, and 2,000-row checks where affected. All native checks use isolated preferences; diagnostic images/logs stay ignored.

## Risks / Trade-offs

- More visible chart area can increase repaint work → compare complete-app cost and avoid rebuilding rows/widgets every tick.
- Small windows cannot display the whole dashboard at once → use vertical scrolling, one-column panels, compact controls, and no horizontal overflow.
- Missing sensors or GPU fields can distort summary layout → preserve named unavailable states, allow wrapping, and hide bars without numeric values.
- The mockup mixes illustrative storage arithmetic and GPU metrics → bind actual independent readings, clearly label VRAM, and use reported capacity instead of copying decorative text.
- GTK shared cell APIs are deprecated but supported on the baseline → retain those efficient renderers and their existing behavioral checks; no unrelated migration.

## Migration Plan

Implement and test with the project environment and isolated test settings. Update the user guide and validation evidence. After checks pass, close only the old Workstation Monitor window normally, relaunch using its existing desktop command, and inspect the live redesigned window. Other workstation jobs stay running. The user's follow-up authorized review and pushing; publish only the privacy-reviewed source tree with the required DCO sign-off.

## Progress

The native implementation and guide are complete. Core/provider checks (26), dashboard/native flows, source-selection failures, focus/exit/partial behavior, offline/fault recovery, fresh-process startup, desktop/narrow/light/dark layouts, and 200% scaling passed. GTK header wrapping and the scrolled grid's minimum-width constraint were corrected using actual native allocations; virtual-display checks compensate for CSD/adaptive allocations before asserting exact content dimensions.

The final short comparison measured 0.780% whole-machine CPU and 132.52 MiB peak RSS, versus 0.674% and 116.34 MiB before. Process inventory changed (542–543 versus 577–587), so this is an equivalent-protocol live diagnostic, not an isolated attribution of the difference to UI changes. Main-thread update p95 was 43.06 ms; grouping/sort p95 was 10.12 ms. Full results and limits are in [validation.md](../../../docs/validation.md); raw local evidence is in `artifacts/sleek-before.json` and `artifacts/sleek-after-final.json`.

The installed user-local command opened the graphite window with the saved appearance preference respected. Two successive captures verified advancing last-sample timestamps and live CPU/GPU/network values. The initial seven tasks are complete.

Pre-publication review corrected an unavailable system sample being mistaken for an empty successful inventory. Focused app rows and details had reported exits, and the footer had reported zero processes. Current counts and row values now remain unavailable after a failed observation; details retain the last successful observation time. Exit labels require an authoritative successful inventory. The native regression covers failure, retained values/timestamps, independent GPU updates, recovery, and confirmed exits at ordinary and 200% scaling.

Retained row actions also carry their actual observation time into details. Member buttons resolve the latest retained member by identity when activated, rather than capturing an older process object when the button was first created. This keeps a cached member's values and timestamp together after an exit or provider failure.

All nine implementation/review tasks passed. An explicit 55-file portable source export and the existing committed history passed local Gitleaks scans; a separate text review found no private home paths, private-network addresses, hardware identifiers, personal email addresses, or binary artifacts. The authorized commit/push follows the gates in [tasks.md](tasks.md) and [publishing.md](../../../docs/publishing.md); delivery receipts stay local and ignored.
