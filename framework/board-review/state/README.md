# Product State Artifacts

**Purpose:** Define the human-readable per-product state files used by persistent product CTO sessions.

**What this covers:**
- The state files each product CTO owns
- Boundaries between product state, precheck state, logs, and live GitHub
- Shared Markdown structure and update rules

Each persistent product CTO owns exactly one Markdown file:

- `churnpilot.md`
- `framework.md`
- `statuspulse.md`
- `personal-brand.md`
- `openclaw-assistant.md`
- `clse.md`

These files are compact cross-run memory for product CTO sessions. They are not routing truth, raw logs, GitHub mirrors, or fleet dashboards.

## Source Boundaries

- GitHub labels/issues decide ticket actionability.
- `../PRECHECK_STATE.json` stores precheck scan/runtime state.
- `../logs/` stores raw per-run execution logs.
- Product state files store only durable notes the same product CTO needs after the current wake exits.

## Shared Structure

Preserve these sections unless there is a clear reason to evolve the contract:

- Routing
- Current State
- Current Blockers
- Active Dispatches
- Handoff Notes

## Update Rules

- Read the product state file on first boot, after compaction, during recovery, or when it may affect the current pass.
- Update it before exit when the pass creates cross-run context.
- Do not duplicate full GitHub ticket history or closed-ticket lists.
- Do not write another product's state file from a product CTO session.
- Promote durable product knowledge to the project README, docs, or plans instead of burying it here.
