# Framework Plans

Planning artifacts for the Framework product — the operational engine behind board review, role orchestration, metrics, and automation.

## Persistent PM Session

- PM session key: `agent:main:pm-framework`
- PM session id: `5b7fab32-ed95-4466-96b0-142d1dca72b9`
- Product: Framework
- Repo: `hendrixAIDev/hendrixAIDev`
- Task queue: `framework/plans/task_queue/tasks.yaml`

The Framework PM is discovery/planning only unless the CTO explicitly expands scope:
- no code edits by default
- no GitHub issue creation by default
- no engineer/QA/reviewer dispatch
- no external actions

## Files

- `task_queue/tasks.yaml` — PM/CTO intake queue for Framework product ideas and planning tasks.
- `org-view-visualization.md` — PM proposal artifact for the organization-view visualization concept, once produced by the Framework PM.
- `org-view-mvp1-implementation-backlog-2026-05-15.md` — PM backlog artifact that decomposes the MVP 1 org summary plus ChurnPilot pilot detail view into CTO-ready implementation tasks.
- `org-view-mvp1-view-contract.md` — PM planning contract that locks the MVP 1 field-level information model, normalized stage framing, visible-role requirements, and v1 exclusions for the read-only org summary plus ChurnPilot pilot detail.
- `org-view-mvp1-view-model-mapping.md` — backend/full-stack planning artifact that maps per-product state files, product task queues, and GitHub issue/status-label state into the MVP 1 org-summary and ChurnPilot-detail view model, including normalized stage and role-chip inference plus sparse-data fallbacks.

## Queue Hygiene

Before or immediately after editing `task_queue/tasks.yaml`, run:

```bash
ruby -e 'require "psych"; Psych.load_file("framework/plans/task_queue/tasks.yaml"); puts "yaml_ok"'
```

Notes:
- YAML single-quoted strings do *not* use backslash escaping for apostrophes. `repo\'s` is invalid there.
- If a note contains an apostrophe, either double it inside single quotes (`repo''s`) or switch that line to double quotes.
- Precheck reads this file directly, so one malformed line can stall the Framework queue scanner.
