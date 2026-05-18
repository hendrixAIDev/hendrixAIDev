# Board Review

**Purpose:** Index the board-review automation system and its maintenance contract.

**What this covers:**
- Core board-review docs and runtime files
- Current CTO-led product orchestration strategy
- Offline contract-test gate
- Migration direction for product state and routing

## Core Docs

- `BOARD_REVIEW.md` — CTO operating guide
- `TICKET_SYSTEM.md` — sub-agent ticket and status rules
- `REPOS.conf` — monitored repos
- `state/README.md` — product state artifact contract
- `tests/README.md` — deterministic offline contract-test expectations
- `docs/ARCHITECTURE.md` — current system architecture
- `workflows/` — workflow examples / references for CTO

## Current Strategy

Board review uses a CTO-led product orchestration model.

Key points:
- one persistent named CTO session per product
- precheck wakes the correct product CTO session
- CTO owns strategy, planning, and next-step decisions
- CTO dispatches isolated work via `skills/dispatch-agent/` (`dispatch.sh`), not `sessions_spawn`
- workflows are references, not a rigid router
- sub-agents work under `status:in-progress`, then normally return tickets to `status:new`
- live GitHub issue labels are authoritative for whether work is actionable
- changes to board-review machinery must pass `bash framework/board-review/tests/run.sh`
- CTO re-triages after each completed work pass
- validation is required before closure
- per-product CTO continuity lives under `state/<product>.md`
- product CTOs update only their own state files during normal passes
- `tools.sessions.visibility = "agent"` allows same-agent coordination among CTO, PM, main webchat, and the parent Slack session via `sessions_send`

## Maintenance Contract Test Gate

Any change to the board-review framework, precheck wake routing, product state contract, task queue intake, or session lock handling must run the offline contract suite before the change is considered complete:

```bash
bash framework/board-review/tests/run.sh
```

This suite is intentionally scoped to deterministic routing and state contracts, not LLM behavior or live GitHub/OpenClaw execution. It should use fixtures and mocked `gh` / `openclaw` commands so it can pass 100% offline.

The stable invariants are:
- live GitHub `status:*` labels are the only actionability source
- no board-review fleet-status Markdown file is read or written as an actionability source
- product wake prompts include the correct product context block: product name, product state path, and task queue path
- precheck writes `PRECHECK_STATE.json` with `actionableIssues` and no stale `openIssues`
- ChurnPilot and Framework task queues route independently to their own CTO sessions and queue files
- live run locks prevent duplicate wakes
- stale or dead run locks are cleared

If this command fails after a framework change, fix the contract break before dispatching or documenting the change as complete.

## Migration Direction

Done so far:
- product CTO session mapping defined in `BOARD_REVIEW.md`
- precheck routes wakes by product CTO session
- `BOARD_REVIEW.md` and `TICKET_SYSTEM.md` aligned around CTO-led re-triage
- shared state artifact contract defined
- starter per-product state files created
- workflow references added
- same-agent session tool visibility enabled for CTO/PM/main/Slack coordination

Next:
- keep live CTO runs writing concise, human-readable product state files consistently
