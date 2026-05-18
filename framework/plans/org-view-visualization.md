# Org View Visualization Proposal

**Date:** 2026-05-09
**Product:** Framework
**Author:** Framework PM session (`agent:main:pm-framework`)

## Recommended visualization concept

Build an **Organization Operations Map** with a default **product-layered board**:

1. **Rows = products**
   - ChurnPilot
   - StatusPulse
   - Framework
   - Personal Brand
   - OpenClaw Assistant
   - CLSE

2. **Columns = operating layers**
   - **Product health** — repo, live status, open actionable work
   - **Role lane** — CTO / PM / Engineer / Reviewer / QA role state
   - **Work stage lane** — queue items, GitHub ticket stage, blockers
   - **Attention lane** — what needs a decision next

3. **Card detail pattern per product**
   - compact status chips for each role
   - active ticket count by stage
   - backlog count from task queue
   - current wake/run state for the mapped product CTO session
   - most important next action

This should feel like a **layered control tower**, not a generic kanban board. The point is to show how work moves from PM discovery → CTO triage → engineer/review/QA → done, per product.

---

## Product/layer model

### Layer 1 — Product summary
Per product, show:
- product name
- repo
- local path
- live URL if any
- product mode/status from `framework/PROJECTS.md`
- open actionable ticket count
- whether a task queue exists

### Layer 2 — Session + workflow state
Per product, show:
- mapped persistent CTO session key/id
- whether the CTO runlock shows active work now
- whether precheck would wake this product
- last known board-review note or last activity timestamp

### Layer 3 — Role state
Per product, show the current visible state of roles:
- **PM** — idle / proposed work exists / triaged artifact ready
- **CTO** — idle / triaging / waiting on in-flight pass / blocked / needs JJ
- **Engineer** — not active / active implementation pass
- **Reviewer** — review requested / review active
- **QA** — verification requested / QA active

### Layer 4 — Work item pipeline
Show two connected sources of work:
- **Task queue items** (PM-owned discovery backlog)
- **GitHub tickets** (execution backlog)

Suggested visual order:
`proposed → triaged → ticketed/in_progress → review → verification → cto-review/done`

Important nuance from the current implementation:
- task queues and GitHub tickets are separate systems
- `status:in-progress` on GitHub means a dispatched pass is active, not that the whole ticket is nearly done
- many products may have no queue at all, so the UI should degrade gracefully

---

## Role status model

Use a small shared vocabulary so the whole org view is scannable.

### PM role states
- **idle** — no pending proposed/triaged queue items
- **backlog** — proposed items exist
- **ready** — triaged artifact ready for CTO intake
- **holding** — queue item awaiting CTO/JJ decision

### CTO role states
- **idle** — no actionable tickets or due queue intake
- **triaging** — `status:new` / queue intake needed
- **coordinating** — a work pass is in flight under `status:in-progress`
- **blocked** — ticket in `status:blocked`
- **needs_jj** — ticket in `status:needs-jj`

### Engineer / Reviewer / QA role states
These should be inferred from ticket state plus dispatch/run data:
- **idle**
- **queued** — next pass requested but not clearly active yet
- **active** — active run / active worktree pass
- **returned** — pass completed and ticket returned to CTO (`status:new`)
- **blocked** — failure or unresolved dependency stopped the pass

### Visualization pattern
Inside each product row, render role chips like:
- PM: Ready
- CTO: Coordinating
- Eng: Active
- Review: Idle
- QA: Idle

That gives JJ/CTO an at-a-glance operating picture without reading ticket logs.

---

## Task/ticket stage model

The current framework already exposes enough stages to model this clearly.

### PM queue stages
From `framework/plans/task_queue/tasks.yaml` schema:
- `proposed`
- `triaged`
- `ticketed`
- `in_progress`
- `blocked`
- `done`
- `rejected`
- `needs_human`

### GitHub / board-review stages
From `framework/board-review/BOARD_REVIEW.md` and `TICKET_SYSTEM.md`:
- `status:new`
- `status:in-progress`
- `status:review`
- `status:verification`
- `status:cto-review`
- `status:blocked`
- `status:needs-jj`
- `status:done`

### Recommended normalized stage groups for the visualization
Use product-facing grouped stages instead of exposing every raw label equally:

1. **Discovery**
   - queue: `proposed`, `triaged`

2. **Ready for CTO**
   - queue backlog due
   - ticket: `status:new`

3. **In execution**
   - queue: `ticketed`, `in_progress`
   - ticket: `status:in-progress`

4. **In review**
   - ticket: `status:review`

5. **In verification**
   - ticket: `status:verification`

6. **Awaiting final decision**
   - ticket: `status:cto-review`, `status:needs-jj`, queue `needs_human`

7. **Blocked**
   - ticket: `status:blocked`, queue `blocked`

8. **Done**
   - queue `done`
   - ticket `status:done` / closed

This gives the org view a stable legend while still mapping back to the real implementation.

---

## Data sources from the current implementation

### Product registry
- `framework/PROJECTS.md`
- `framework/board-review/REPOS.conf`

Use these for:
- product list
- repo mapping
- local path
- live URL

### Workflow rules + canonical statuses
- `framework/board-review/BOARD_REVIEW.md`
- `framework/board-review/TICKET_SYSTEM.md`
- `framework/roles/README.md`
- `framework/roles/CONVENTIONS.md`

Use these for:
- role vocabulary
- stage definitions
- persistent CTO session mapping
- workflow semantics

### Human-facing fleet summary

Use this for:
- context/history only
- human-readable fleet notes
- optional provenance links

Do not use this for ticket actionability, role state, active-work counts, or product continuity state.

### Product state artifacts
- `framework/board-review/state/README.md`
- `framework/board-review/state/<product>.md`

Use these for:
- compact per-product durable state
- product-specific routing notes once they exist

### PM queue data
- `framework/plans/task_queue/tasks.yaml`
- any future product-local queues using the same pattern

Use these for:
- proposed/triaged discovery backlog
- PM notes
- whether a product has unpromoted work waiting for CTO intake

### Automation / wake state
- `skills/board-review-precheck/scripts/precheck.sh`

Use this for:
- repo → product mapping
- product → CTO session mapping
- queue-backed wake logic
- queue backlog detection rules
- runlock files and active-session hints

---

## Suggested MVP slices

### MVP 1 — ChurnPilot pilot detail page with org summary
Goal: prove the model in a read-only JJ-facing view using per-product state files, product task queues, and GitHub issue/status-label state as the initial source of truth.

Show:
- a compact org-wide summary above the fold
- a ChurnPilot detail page as the pilot product
- product summary for ChurnPilot
- open actionable ticket count
- active issue titles
- all active role chips inferred from current board-review state
- queue/ticket stage summary using the normalized stage groups

Why first:
- matches JJ's preferred viewing mode: org-wide summary first, then one product detail page
- keeps the first release read-only and clean
- uses the existing product state, queue, and ticket model before introducing deeper runlog/session reconciliation
- limits scope by piloting on ChurnPilot before going cross-product

### MVP 2 — Active CTO session awareness
Add:
- persistent CTO session key/id
- runlock active/idle signal
- last wake reason if available
- “waiting on active pass” vs “ready for CTO” distinction

Why second:
- this is where the org view becomes operational instead of just descriptive

### MVP 3 — Cross-product expansion
Add:
- the same summary/detail model for all mapped products
- consistent product switching between product detail views
- clearer per-product role and stage comparisons from the org-wide summary

Why third:
- proves the model on ChurnPilot first before scaling it across the whole organization

### MVP 4 — Timeline / flow analytics
Later, add:
- retry loops
- stalled passes
- time in stage
- repeated watchdog resets

Why this matters:
- the current board-review system clearly experiences workflow friction (for example repeated review resets), and the visualization should eventually expose that pattern, not hide it.

---

## Resolved product direction (JJ answers)

1. **Primary audience:** JJ first. This should optimize for a business/control view before deeper CTO operations use.
2. **Initial information architecture:** one product detail page with an org-wide summary above it, rather than a single flat board-only experience.
3. **Role granularity:** show all active roles, not only PM / CTO / Engineer / Review / QA.
4. **Initial source of truth:** start from per-product state files, product task queues, and GitHub issue/status-label state.
5. **Pilot product:** use ChurnPilot as the first pilot product.
6. **Stall visibility in v1:** keep MVP clean and focused on current state; defer retry-loop and watchdog-reset visibility.
7. **Interaction model:** read-only first.

---

## Recommendation

I recommend a **read-only JJ-facing org summary + ChurnPilot detail view** as the first implementation target:
- **org-wide summary first** for quick business/control scanning
- **one ChurnPilot detail page** as the pilot product view
- **all active role chips** visible for the pilot product
- **queue/ticket stage summary** based on normalized stages
- **current-state clarity over workflow diagnostics** in v1

That matches JJ's stated preferences while still fitting the framework’s actual architecture today: products are the top-level unit, CTO sessions are product-bound, roles are pass-based, and work moves through queue + GitHub stages rather than a single monolithic backlog.

The main thing to avoid is a generic kanban that loses the distinction between:
- PM discovery backlog
- CTO orchestration state
- active execution roles
- GitHub ticket stage

That distinction is the real shape of the current system, and the visualization should make it obvious even in a more JJ-friendly summary/detail presentation.
