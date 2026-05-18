# Board Review Architecture

**Purpose:** Describe the current board-review automation architecture without duplicating the operational runbook.

**What this covers:**
- System boundaries and sources of truth
- How precheck, product CTO sessions, sub-agents, GitHub, and state files interact
- Current session, routing, validation, and documentation responsibilities

`BOARD_REVIEW.md` is the CTO operating guide. This file is the architecture reference for how the pieces fit together.

---

## System Model

Board review is a product-specific orchestration loop.

The system does not run as one long-lived worker waiting for every task to finish. Instead:

1. A lightweight precheck script scans live GitHub issue labels.
2. When actionable work exists, precheck wakes the matching persistent product CTO session.
3. The product CTO performs one orchestration pass.
4. The CTO dispatches isolated sub-agents when work is needed.
5. Sub-agents update GitHub issue comments and labels before exiting.
6. Precheck sees the next actionable label change and wakes the CTO again.

The persistent part is the product CTO session identity and product state artifact, not an always-running process.

---

## Main Components

| Component | Current responsibility |
|---|---|
| GitHub issues and labels | Operational source of truth for ticket actionability |
| `skills/board-review-precheck/scripts/precheck.sh` | Scans repos and wakes the correct product CTO session |
| `skills/board-review-precheck/scripts/watchdog.sh` | Resets stale `status:in-progress` tickets to `status:new` |
| Product CTO session | Triages, plans, chooses next action, workflow, role, and validation plan |
| `skills/dispatch-agent/scripts/dispatch.sh` | Starts isolated one-shot sub-agent jobs from CTO-authored prompts |
| Sub-agents | Execute narrow work and return results through GitHub |
| `framework/board-review/state/<product>.md` | Compact product continuity for the matching CTO session |
| `framework/board-review/PRECHECK_STATE.json` | Runtime scan/cache state for precheck only |
| `framework/board-review/workflows/` | Reference workflow templates for CTO triage |

---

## Sources Of Truth

GitHub issue labels decide whether a ticket is actionable. `PRECHECK_STATE.json` is only a runtime cache and must not override live GitHub state.

Product state files under `framework/board-review/state/` store compact cross-run context for each product CTO. They are not ticket mirrors, raw logs, or fleet dashboards.

`BOARD_REVIEW.md` owns CTO run behavior. `TICKET_SYSTEM.md` owns sub-agent ticket rules. `framework/roles/CONVENTIONS.md` owns engineering standards shared by roles.

---

## Session Architecture

Each product has a dedicated persistent CTO session key:

| Product | Session key | Repos |
|---|---|---|
| ChurnPilot | `agent:main:churnpilot-cto` | `hendrixAIDev/churn_copilot_hendrix` |
| StatusPulse | `agent:main:statuspulse-cto` | `hendrixAIDev/statuspulse` |
| Framework | `agent:main:framework-cto` | `hendrixAIDev/hendrixAIDev` |
| Personal Brand | `agent:main:personal-brand-cto` | `hendrixAIDev/hendrixaidev.github.io` |
| OpenClaw Assistant | `agent:main:openclaw-assistant-cto` | `zrjaa1/openclaw-assistant` |
| CLSE | `agent:main:clse-cto` | `hendrixAIDev/character-life-sim` |

Normal CTO wakes reuse existing session context. After compaction or recovery, the CTO reloads the minimum context defined in `BOARD_REVIEW.md` and `CTO_PROMPT.md`.

The main webchat session is not the product CTO. It may inspect or repair automation, but it does not run the board-review workflow.

---

## Routing Flow

The normal control flow is:

```text
OS cron / launchd
-> precheck.sh
-> live GitHub label scan
-> product CTO session wake
-> CTO triage, planning, and dispatch decision
-> dispatch.sh
-> isolated sub-agent run
-> GitHub comment + label update
-> next precheck wake
```

Precheck wakes on `status:new`, where the CTO decides the next step. Review, validation, retry, escalation, and closure are CTO-selected actions from that state, not separate normal status phases.

`status:in-progress` means a dispatched work pass is active. The watchdog resets stale in-progress tickets back to `status:new` so the CTO can re-triage them.

---

## CTO Responsibilities

The product CTO owns orchestration, not implementation.

Current CTO responsibilities:

- classify each actionable ticket
- plan the next step before delegating
- choose the next workflow and role
- define the validation plan before closure
- set active labels before dispatch
- use `dispatch.sh` for board-review sub-agent work
- update the product state file when cross-run context matters
- escalate to `status:needs-jj` only for genuine CEO decisions
- close tickets only after the validation standard is met
- exit after one pass instead of waiting on sub-agents

The CTO should not hide critical state only in chat context, implement product code directly, or wait inside the same run for sub-agent completion.

---

## Sub-Agent Responsibilities

Sub-agents are isolated execution workers.

They must:

- follow the CTO-authored prompt, referenced role materials, and ticket scope
- leave evidence in the GitHub issue
- update the issue label before exiting
- verify the label change succeeded

They do not own product strategy, global workflow decisions, long-term product memory, or CEO escalations.

---

## Workflow And Validation Model

The CTO chooses from reference workflows instead of following one fixed pipeline for every ticket.

Current workflow references:

- `workflows/feature-implementation.md`
- `workflows/bugfix.md`
- `workflows/product-analysis.md`
- `workflows/ux-design.md`
- `workflows/trust-risk.md`
- `workflows/content-launch.md`

Every ticket needs explicit validation before closure. QA is one validation mode, not the only mode. For example, a user-facing UI change may need browser QA, while a product-analysis ticket may need CTO review and follow-up ticket creation.

---

## State Boundaries

Use each state artifact for its intended job:

| Artifact | Use | Do not use for |
|---|---|---|
| GitHub issue | ticket status, evidence, labels, acceptance criteria | private strategy notes |
| `state/<product>.md` | compact product continuity | full ticket history or raw logs |
| `PRECHECK_STATE.json` | precheck runtime cache | product continuity or actionability truth |
| `logs/` | raw run records | curated operating state |
| project README/docs/plans | durable product knowledge | temporary pass bookkeeping |

Durable product decisions belong in the relevant project docs or plans. Temporary pass details belong in GitHub comments, logs, or daily memory when needed.

---

## Maintenance Gate

Changes to board-review routing, precheck behavior, product state contracts, task queue intake, or session lock handling must pass:

```bash
bash framework/board-review/tests/run.sh
```

That test suite verifies deterministic architecture contracts offline, including label-based actionability, product wake prompt context, queue routing, runtime state shape, and run-lock handling.
