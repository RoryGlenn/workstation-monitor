# Workstation Monitor

This project is a native, read-only Ubuntu performance monitor. The behavior contracts and implementation tasks live in `openspec/changes/build-local-task-manager/`.

- Use OpenSpec before development by default. Small, straightforward changes may skip it; substantial work must create or update a change with the goal, requirements, design, tasks, and validation criteria before coding. Read the change when resuming and keep progress and remaining work current.

- Keep runtime data local. No network services, analytics, automatic uploads, root helpers, packet capture, or cloud dependencies.
- Preserve field-level availability. Unknown, denied, warming, and stale data must not become zero. A missing optional field must not hide a process.
- Keep CPU percentages on the whole-machine 0–100% scale; label RSS and partial group totals honestly.
- Update GTK only on its main thread; keep collector results bounded and histories limited to five minutes.
- Preserve existing user work and running workloads. Use fixtures and disposable local workloads for tests; do not restart or stress active GPU jobs.
- For all documentation, read and apply the installed `doc-agent` skill's `SKILL.md`. Keep the README and user guide consistent with actual controls and launch commands.
- Use `.venv/bin/python -m unittest discover -s tests -v` for core checks. Native integration checks are documented in `tests/README.md`.
- Do not create issues, commits, pushes, PRs, or merges without authorization. Authorized commits need a DCO sign-off; preserve configured cryptographic signing separately.
- Before public delivery, follow `docs/publishing.md`. Keep workstation captures, raw diagnostics, local settings, home paths, credentials, and private email addresses out of Git.
