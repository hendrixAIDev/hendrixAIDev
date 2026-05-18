# Framework State

**Purpose:** Preserve compact cross-run continuity for the Framework product CTO session.

**What this covers:**
- Product identity and routing
- Current result, blockers, and active dispatches
- Durable handoff notes for future Framework CTO wakes

## Routing

| Field | Value |
|---|---|
| Product | Framework |
| Slug | framework |
| Session key | `agent:main:framework-cto` |
| Session id | resolved at runtime |
| Repos | `hendrixAIDev/hendrixAIDev` |
| Primary README | `framework/README.md` |
| Task queue | `framework/plans/task_queue/tasks.yaml` |
| Updated by | main-session |

## Current State

| Field | Value |
|---|---|
| Last run at | 2026-05-16T08:18:00Z |
| Last result | Context refresh only. Reloaded current board-review operating docs, the Framework state artifact, and the configured Framework task queue without running a board-review pass or mutating GitHub workflow state. |

## Current Blockers

- None.

## Active Dispatches

- None.

## Handoff Notes

- Framework queue intake must use `framework/plans/task_queue/tasks.yaml`, not the ChurnPilot queue.
- Persistent CTO-session GitHub auth divergence has appeared before; compare against live precheck state before escalating.
- 2026-05-16 01:18 PDT - Refreshed resident context after major doc/prompt updates by rereading AGENTS.md, SECURITY_PROTOCOL.md, PROJECT_STRUCTURE.md, DOCUMENTATION.md, BOARD_REVIEW.md, CTO_PROMPT.md, TICKET_SYSTEM.md, CONVENTIONS.md, this state file, and `framework/plans/task_queue/tasks.yaml`. No board-review execution was performed.
