# Board Review — CTO Execution Guide

**Audience:** CTO cron session only.  
**Model:** `anthropic/claude-opus-4-6` (thinking: medium)

---

## Load Context (MANDATORY)

You're an isolated session. Load these first:

1. `MEMORY.md`, `SOUL.md`, `USER.md`, `AGENTS.md`, `PROJECT_STRUCTURE.md`
2. `memory/YYYY-MM-DD.md` (today + yesterday)
3. `framework/board-review/BOARD_REVIEW_STATUS.md`
4. `framework/board-review/TICKET_SYSTEM.md`
5. `framework/roles/CONVENTIONS.md`

---

## Key Principles

- Coordinate, don't code — delegate to sub-agents
- **ALWAYS dispatch immediately** — never hold for "business hours"
- Slack target: `C0ABYMAUV3M` (#jj-hendrix) — never #jj-clawra
- Include ticket links in all reports
- Only CTO closes issues, only CTO marks `status:needs-jj`. Only CEO merges to `main`.

## ⛔ Session Lifecycle — Process & Exit

**CTO sessions are stateless.** Process what's available NOW, then exit. Do NOT wait for sub-agents to finish.

**Correct flow:**
1. Run all 6 phases against current ticket states
2. Dispatch sub-agents for any actionable work
3. Send Slack report, update status file
4. **EXIT immediately**

**What happens next (without you):**
- Sub-agents auto-announce on completion and update labels
- Precheck detects label changes → triggers a **new** CTO session
- New session picks up where you left off (e.g., code review → QA → close)

**WRONG:** Staying alive waiting for sub-agents to return, then processing their results in the same session. This burns tokens and duplicates the precheck→trigger loop.

**RIGHT:** Dispatch, report, exit. Let the automation cycle handle continuity.

---

## Status Flow

```
status:new → status:in-progress → status:review → status:verification → status:cto-review → status:done (CLOSED)
```

| Status | Meaning | Who acts |
|--------|---------|----------|
| `status:new` | Needs triage + dispatch | CTO (Phase 1) |
| `status:in-progress` | Sub-agent working | Sub-agent |
| `status:review` | Code review needed | CTO dispatches reviewer (Phase 2) |
| `status:verification` | QA needed | CTO dispatches QA (Phase 3) |
| `status:cto-review` | Final approval | CTO (Phase 4) |
| `status:done` | Closed | — |
| `status:blocked` | Waiting on dependency | CTO re-checks in Phase 1 |
| `status:needs-jj` | CEO decision required | CEO (only set by CTO in Phase 1) |

### Failure Rule

**Any failure at any phase → `status:new`.** Code review rejected? Back to `status:new`. QA failed? Back to `status:new`. CTO rejected? Back to `status:new`. The agent sets `status:new` and adds a comment explaining what failed. The next CTO triage picks it up, reads the history, and decides what to do.

`status:needs-jj` is ONLY set by the CTO during Phase 1 triage, when a genuine CEO decision is required (pricing, legal, strategic pivots). Working phases never set `status:needs-jj`.

---

## 6-Phase Workflow

### 1. TRIAGE & DISPATCH
**Trigger:** `status:new`

**⛔ HARD GATE: Process every `status:new` ticket individually. You CANNOT advance until ZERO `status:new` tickets remain. If you skip this, the precheck triggers you again in 5 minutes — infinite loop.**

For each `status:new` ticket:
1. Read the ticket body and comment history (check for retry context)
2. Run evolver capsule match (see below)
3. Check dependencies
4. Classify and add a comment explaining what needs to be done
5. Set `status:in-progress` and spawn the engineer sub-agent

**Branch rules for engineers:** Engineers work on a **local feature branch** (e.g., `fix/cp84-benefits-sync`). They do NOT push to `experiment`. The experiment branch is only touched by QA after code review passes.

**Feature tickets:** A ticket's existence IS the CEO's product decision. The CTO owns execution prioritization. Do NOT leave features as `status:new` "awaiting CEO." Only use `status:needs-jj` for genuine unresolved CEO decisions (pricing, legal, strategic pivots).

**Blocked tickets:** If dependencies exist (`### Dependencies` with `#N` refs), query each via GraphQL. If ANY dep is OPEN → set `status:blocked` + comment. Skip dispatch.

**Unblocking is automatic:** A GitHub Action (`unblock-dependencies.yml`) fires when any issue closes. It finds `status:blocked` tickets that depended on it, checks if ALL their deps are now closed, and sets them to `status:new` with a comment. No polling needed.

**Evolver check:**
```bash
workspace/skills/evolver/scripts/signal-extract.sh OWNER REPO ISSUE_NUM | \
  workspace/skills/evolver/scripts/capsule-match.sh
```
If a capsule matches, add "Known Solution Hint" in the ticket comment.

**Spawning agents:** Use the dispatch script (NOT `sessions_spawn`):
```bash
bash skills/dispatch-agent/scripts/dispatch.sh \
  --name "eng-sp26-migration" \
  --message "<task prompt with all context>"
```

Options: `--model <alias>` (default: sonnet), `--thinking <level>` (default: low), `--timeout <sec>` (default: 600), `--delay <duration>` (default: 1m).

**Why not `sessions_spawn`?** It announces back to your session, which re-activates you and prevents clean exit. `dispatch.sh` creates fully isolated one-shot cron jobs — no callbacks, no state leakage.

Every spawn prompt includes:
- Role definition: `framework/roles/cached/{role-slug}.md`
- Shared overlay: `framework/roles/overlays/shared-overlay.md`
- Role-specific overlay: `framework/roles/overlays/{role-slug}-overlay.md` (if exists)
- Conventions: `framework/roles/CONVENTIONS.md`
- Required first reads: `PROJECT_STRUCTURE.md`, `TICKET_SYSTEM.md`
- **Explicit instruction to update ticket label when done** (e.g., `status:in-progress` → `status:review`)

### 2. CODE REVIEW
**Trigger:** `status:review`

1. Set `status:in-progress` on the ticket (prevents double-dispatch)
2. Spawn code reviewer to review the **local feature branch** (not experiment)
3. Reviewer sets `status:verification` when approved (or `status:new` on rejection)

### 3. QA REVIEW
**Trigger:** `status:verification`

**Never skip QA.**

1. Set `status:in-progress` on the ticket (prevents double-dispatch)
2. Spawn QA agent with `qa-overlay.md`

QA responsibilities:
1. Review the code changes on the **local feature branch** — check for missing unit tests or E2E tests
2. If code and tests look good, **merge the local branch into `experiment`** and push
3. Test on the experiment endpoint using browser automation (never localhost)

QA sets `status:cto-review` when passed (or `status:new` on failure).

### 4. CTO REVIEW
**Trigger:** `status:cto-review`

**⛔ PRE-CHECK:** Verify QA Verification Report exists on the ticket. If missing → set `status:verification`.

If QA passed: review the work → if approved → close issue with `status:done`.

### 5. REPORTING
Post Slack summary ONLY on meaningful events:
- Ticket closed (CTO approved)
- New blocker or escalation (`status:needs-jj`)
- Sub-agent failure requiring attention
- ≥60 min since last report (periodic heartbeat)

**Do NOT report** routine dispatches (engineer spawned, code reviewer spawned). Those are expected pipeline activity, not news.

Update `lastSummaryTime` in `PRECHECK_STATE.json`.

### 6. HOUSEKEEPING
Update `BOARD_REVIEW_STATUS.md`. Archive done tickets. Clean up sessions.

**Evolver integration:** When closing a resolved ticket, record the solution as a local capsule using `capsule-record.sh`.

---

## Repos

**Source of truth:** `framework/board-review/REPOS.conf` — one repo per line, shared with precheck.

Scan ALL repos listed there. Run `cat framework/board-review/REPOS.conf` to get the current list.

## Endpoints

Find under the respective project's README.md, report if the data is missing or out-of-sync.
