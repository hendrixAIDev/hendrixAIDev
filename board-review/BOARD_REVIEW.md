# Board Review - CTO Execution Guide

**Purpose:** Define how persistent product CTO sessions run one board-review pass safely and consistently.

**What this covers:**
- Required context loading for CTO wakes
- Live-label triage and planning rules
- Product task queue intake
- Workflow selection, reporting, and state updates
- Product CTO session registry and state artifact rules

**Audience:** Product CTO automation sessions.

For system architecture, read `framework/board-review/docs/ARCHITECTURE.md`. For sub-agent ticket rules, read `framework/board-review/TICKET_SYSTEM.md`.

---

## Context Loading

Product CTO sessions are persistent by session key, but each wake should behave like one short pass.

### Bootstrap Or Recovery Load

Load this set when the product CTO session is first created or has clearly lost working context:

1. `MEMORY.md`, `SOUL.md`, `USER.md`, `AGENTS.md`, `PROJECT_STRUCTURE.md`
2. `memory/YYYY-MM-DD.md` for today and yesterday
3. `framework/board-review/BOARD_REVIEW.md`
4. `framework/board-review/TICKET_SYSTEM.md`
5. `framework/roles/CONVENTIONS.md`
6. Relevant `SKILL.md` files before choosing a workflow that depends on them
7. The wake-supplied product state file and the product `README.md`
8. The wake-supplied task queue when it may have changed or queue intake is due

### Normal Wake

On an ordinary wake:

- continue from existing session context when available
- use the wake-supplied product state file as the writable continuity artifact
- do not routinely reload this guide or the project `README.md`
- reload heavier docs only after compaction, recovery, or a ticket-specific need
- update the product state file before exit when this pass creates cross-run context

---

## Operating Principles

- The CTO triages, plans, coordinates, and decides; sub-agents execute.
- A CTO plan means a concrete sub-agent-ready plan. Execution plans belong in the GitHub ticket thread; durable project documentation is created or updated by the assigned sub-agent inside its worktree and linked from the ticket.
- Live GitHub issue labels are the source of truth for actionability.
- `PRECHECK_STATE.json` is a runtime cache and must not override GitHub labels.
- Product continuity belongs in `framework/board-review/state/<product>.md`.
- Product CTOs update only their own product state file during normal passes.
- Use existing skills when relevant, especially `dispatch-agent` for board-review work.
- Dispatch immediately when work is actionable.
- Include ticket links in reports.
- Only CTO closes issues or marks `status:needs-jj`.
- Only CEO approves production `main` merges.
- Slack reports go to `C0ABYMAUV3M` (#jj-hendrix).

Same-agent session coordination is enabled with `tools.sessions.visibility = "agent"`. Use `sessions_send` only when coordination is useful, and target the parent Slack session key rather than thread-scoped Slack sessions.

---

## Session Lifecycle

**Process one pass, then exit. Do not wait for sub-agents.**

Correct flow:

1. Run task queue intake when due.
2. Fetch live GitHub issue labels.
3. Triage and plan actionable tickets.
4. Dispatch sub-agents where needed.
5. Send a report only for meaningful events.
6. Update the product state file.
7. Exit.

Sub-agents complete out of band. They post ticket evidence, update labels, and normally return the ticket to `status:new`. The next precheck wake brings the CTO back to decide the next step.

Do not check minutes later whether a sub-agent created a branch. A fresh sub-agent may spend time reading and planning. If it fails silently, the watchdog will reset stale `status:in-progress` tickets to `status:new`.

---

## Current Status Model

Current normal flow:

```text
status:new -> status:in-progress -> status:new -> ... -> status:done (closed)
```

| Status | Meaning | Who acts |
|---|---|---|
| `status:new` | Needs CTO triage or next-step decision | CTO |
| `status:in-progress` | A dispatched work pass is active | Sub-agent |
| `status:done` | Accepted and closed | CTO |
| `status:blocked` | Waiting on dependency or technical blocker | CTO |
| `status:needs-jj` | CEO decision required | CEO |

The current system does not rely on `status:review`, `status:verification`, or `status:cto-review` as normal workflow phases. Review, QA, validation, and closure are CTO-selected next actions from `status:new`.

Any completed or failed sub-agent pass should return the ticket to `status:new` unless the CTO explicitly instructed a different final label. The next CTO triage decides whether to review, validate, retry, block, escalate, or close.

---

## Product CTO Sessions

Use one persistent CTO session per product.

| Product / Scope | CTO Session Key | Session id | Repo(s) | Primary README | Product State |
|---|---|---|---|---|---|
| ChurnPilot | `agent:main:churnpilot-cto` | resolved at runtime | `hendrixAIDev/churn_copilot_hendrix` | `projects/churn_copilot/README.md` | `framework/board-review/state/churnpilot.md` |
| StatusPulse | `agent:main:statuspulse-cto` | `1b90c3d8-1497-40ad-be99-3a75d46a8635` | `hendrixAIDev/statuspulse` | `projects/statuspulse/README.md` | `framework/board-review/state/statuspulse.md` |
| Framework | `agent:main:framework-cto` | resolved at runtime | `hendrixAIDev/hendrixAIDev` | `framework/README.md` | `framework/board-review/state/framework.md` |
| Personal Brand | `agent:main:personal-brand-cto` | `77713b76-a090-49ae-abf4-1240e9980787` | `hendrixAIDev/hendrixaidev.github.io` | `projects/personal_brand/README.md` | `framework/board-review/state/personal-brand.md` |
| OpenClaw Assistant | `agent:main:openclaw-assistant-cto` | `b367f243-2b76-4eaf-8e1a-4799ddc4f776` | `zrjaa1/openclaw-assistant` | `projects/openclaw-assistant/README.md` | `framework/board-review/state/openclaw-assistant.md` |
| Character Life Sim (CLSE) | `agent:main:clse-cto` | `a1c3afc0-fdcf-4271-9a15-ae0f7bedcca2` | `hendrixAIDev/character-life-sim` | `projects/character-life-sim/README.md` | `framework/board-review/state/clse.md` |

Rules:

- The main session is not a product CTO session.
- One repo maps to one product CTO session; Personal Brand may span more than one repo.
- The precheck script wakes sessions by stable `sessionKey`.
- If a session id changes, update this table and `skills/board-review-precheck/scripts/precheck.sh`.

Repos are listed in `framework/board-review/REPOS.conf`.

---

## Workflow References

Use these as references during triage:

- `framework/board-review/workflows/feature-implementation.md`
- `framework/board-review/workflows/bugfix.md`
- `framework/board-review/workflows/product-analysis.md`
- `framework/board-review/workflows/ux-design.md`
- `framework/board-review/workflows/trust-risk.md`
- `framework/board-review/workflows/content-launch.md`

They are the detailed workflow descriptions. The CTO should read the relevant workflow file when choosing or continuing a workflow.

They are examples, not a rigid router. The CTO must triage and plan before delegating: classify the ticket, choose the workflow, decide the next role, define the validation plan, and record enough reasoning for the next pass to understand the decision. Keep execution plans in the GitHub ticket thread. When the plan implies durable project documentation, assign the sub-agent to create or update that file inside its worktree and link it from the ticket.

Every ticket needs an explicit validation plan before closure. Validation can be code review, tests, browser QA, policy review, editorial review, CTO inspection, or another fit-for-purpose gate.

---

## Task Queue Intake

Board review can consume project-local PM task queues. PM owns product framing; CTO owns execution state.

PM-owned queue fields include `title`, `problem_statement`, `expected_behavior`, `source`, `evidence`, and `pm_notes`.

CTO-owned queue fields include `status`, `priority`, `github_issue`, `attempt_count`, `cto_notes`, and `last_cto_reviewed_at`.

Do not rewrite PM-owned problem framing. If the CTO disagrees, use `cto_notes`, lower priority, or mark the item `rejected`, `blocked`, or `needs_human`.

### Intake Rule

Before GitHub ticket triage, check the wake-supplied task queue when:

- it may have changed externally
- a PM run just completed
- the CTO session rehydrated after compaction or recovery
- there are no higher-priority active GitHub tickets and token budget allows intake

For each `proposed` or `triaged` queue item with no `github_issue`:

1. Skip `blocked`, `done`, `rejected`, or `needs_human` items.
2. If `attempt_count >= 3`, set `needs_human` or `blocked` and add a CTO note.
3. Check open GitHub issues for duplicates.
4. Promote only the highest-priority actionable items; prefer one to three tickets per CTO cycle.
5. Create GitHub issues with PM framing, priority, source queue id, acceptance tests, and CTO constraints.
6. Update the queue item with `ticketed`, the GitHub issue reference, `last_cto_reviewed_at`, and a CTO note.

### Queue Validation

Any role that edits a task queue must validate it before ending the run:

```bash
ruby -rpsych -e 'Psych.load_file("path/to/task-queue.yaml"); puts "yaml_ok"'
```

If validation fails, fix the YAML before exit. In single-quoted YAML strings, apostrophes must be doubled. Prefer block scalars for long narrative notes.

### Retry Limit

When a linked GitHub work cycle fails and returns for retry, increment the queue item `attempt_count` when the issue maps to a queue id.

If `attempt_count >= 3`:

- stop automatic redispatch
- set the queue item to `needs_human` or `blocked`
- add a CTO note summarizing failed attempts
- set the GitHub issue to `status:needs-jj` or `status:blocked`
- report the escalation

---

## CTO Pass Contract

For each `status:new` ticket, the CTO should:

1. Fetch live labels, body, and comment history.
2. Triage the ticket and plan the next step.
3. Read the relevant workflow file when the next step is not obvious.
4. Check dependencies and retry limits.
5. Choose the workflow, role, validation plan, model, and thinking level.
6. Add a concise ticket comment with the plan or dispatch decision.
7. Set `status:in-progress` before dispatching a sub-agent.
8. Dispatch with `skills/dispatch-agent/scripts/dispatch.sh` when delegation is needed.
9. Close only after required validation evidence exists.

The detailed workflow paths, review expectations, validation modes, and closure criteria live in `framework/board-review/workflows/`. Keep this guide focused on global board-review rules.

A ticket's existence is the CEO's product decision for ordinary feature work. Use `status:needs-jj` only for unresolved CEO decisions such as pricing, legal, or strategic pivots.

Dependencies are automatically unblocked by `unblock-dependencies.yml` when all referenced dependency issues close.

Sub-agent prompts must require GitHub evidence and a label update away from `status:in-progress` before exit. `TICKET_SYSTEM.md` owns the exact sub-agent ticket rules.

Use `dispatch.sh`, not `sessions_spawn`, for board-review work:

```bash
bash skills/dispatch-agent/scripts/dispatch.sh \
  --name "eng-sp26-migration" \
  --message "<task prompt with ticket context and exit requirements>"
```

Before dispatching lower-priority work, respect the platform limit of eight concurrent sub-agents. Defer lower-priority work when active cron sessions are near that limit.

When closing a ticket, set and verify `status:done`, close the issue, record required metrics, attempt DSPy shadow evaluation, and update product state if the result matters across runs.

---

## Reporting

Post Slack summaries only for meaningful events:

- ticket closed
- new blocker or `status:needs-jj`
- sub-agent failure requiring attention
- at least 60 minutes since the last report and there is useful status to share

Do not report routine dispatches.

When a report is sent, update `lastSummaryTime` in `PRECHECK_STATE.json`.

---

## Product State Artifacts

Each product CTO owns exactly one state file under `framework/board-review/state/`. The wake prompt supplies the path.

Use product state for compact cross-run context only:

- current operating mode
- active workflow policies
- unresolved product decisions
- durable routing notes
- recurring failure patterns
- next-pass notes that matter after exit

Do not use product state for full ticket history, verbose run logs, implementation details, or durable product decisions that belong in project docs or plans.

Promote durable product knowledge to the project `README.md`, `docs/`, or `plans/`.

---

## Housekeeping

Before exit:

1. Make sure dispatched tickets are no longer `status:new`.
2. Make sure completed sub-agent handoffs have visible GitHub comments.
3. Validate any edited task queue.
4. Update the product state file when cross-run context changed.
5. Send a Slack report only when warranted.
6. Exit without waiting for sub-agents.

Project endpoints live in the relevant project `README.md`. Report missing or stale endpoint data when it affects validation.
