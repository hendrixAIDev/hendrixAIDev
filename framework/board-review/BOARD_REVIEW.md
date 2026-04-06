# Board Review — CTO Execution Guide

**Audience:** CTO cron session only.  
**Model:** `openai-codex/gpt-5.4` (thinking: medium)

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

**WRONG:** Checking on a sub-agent's progress minutes after dispatch and declaring it "failed" because no branch/commit exists yet. Sub-agents may spend 5-15 minutes reading code, understanding the codebase, and planning before creating a branch. You have NO way to know if a sub-agent is still working or has truly failed within a single CTO session.

**RIGHT:** Dispatch, report, exit. Let the automation cycle handle continuity. If a sub-agent truly failed (crashed, timed out, exited without work), the ticket will remain `status:in-progress` with no label change. The precheck's stale-ticket detection (>45 min no activity) will reset it to `status:new` for the next CTO cycle. That is the ONLY mechanism for detecting engineer failure — not CTO judgment calls minutes after dispatch.

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

**Any failure at any phase → `status:new`.** Code review rejected? Back to `status:new`. QA failed? Back to `status:new`. CTO rejected? Back to `status:new`. The agent sets `status:new` and adds a comment explaining what failed. The next CTO triage picks it up, reads the history, and re-dispatches an **engineer** to address the feedback.

**⛔ CRITICAL:** `status:new` ALWAYS means "dispatch an engineer." Never short-circuit by dispatching a reviewer or QA agent directly from triage. The status flow is linear: engineer → CR → QA → CTO review. When any phase rejects, it resets to engineer. The CTO must not skip steps or re-run the same phase on unchanged code.

`status:needs-jj` is ONLY set by the CTO during Phase 1 triage, when a genuine CEO decision is required (pricing, legal, strategic pivots). Working phases never set `status:needs-jj`.

---

## 6-Phase Workflow

### 1. TRIAGE & DISPATCH
**Trigger:** `status:new`

**⛔ HARD GATE: Process every `status:new` ticket individually. You CANNOT advance until ZERO `status:new` tickets remain. If you skip this, the precheck triggers you again in 5 minutes — infinite loop.**

For each `status:new` ticket:
1. Read the ticket body and comment history (check for retry context)
2. **Acceptance Tests check:** If the ticket lacks an `## Acceptance Tests` section and is a feature or bug ticket, add one before dispatching. Define 3-5 named test cases that capture the expected behavior. This is the TDD spec — engineers write these tests first.
3. **⛔ 3-ROUND LIMIT:** Count how many completed engineer rounds this ticket has been through. A "round" is a full cycle where the ticket went through engineer dispatch and came back to `status:new` due to failure at ANY stage — engineer produced no work, code review rejected, QA failed, or CTO review rejected. All of these count as failed rounds. If the ticket has already completed 3 full engineer rounds (i.e., round count > 3), do NOT dispatch again — set `status:needs-jj` with a comment summarizing all attempts and why they failed. This prevents dead loops that waste tokens.
3. Run evolver capsule match (see below)
4. Check dependencies
5. Classify and add a dispatch comment that includes:
   - Role being dispatched (e.g., Backend Engineer, Fullstack Engineer, Frontend Engineer, QA Engineer)
   - Model and thinking level (e.g., `Model: Opus, Thinking: Medium`)
   - Brief description of the task
   - Example: `Dispatching: Fullstack Engineer (Model: Opus, Thinking: Low) to implement shared render_quota_banner() helper and unify both sections.`
   - For engineering tickets touching UI, API, database queries, or user-facing behavior, explicitly require the engineer handoff checklist in the ticket comment before `status:review`:
     - synced/rebased from latest `origin/experiment`
     - tested locally on `http://localhost:<port>` (any localhost port is acceptable)
     - brief note on what was verified
     - relevant tests passed

**Role selection guide:**
   - **Fullstack Engineer** (`fullstack-engineer`) — Default for Streamlit projects (ChurnPilot, StatusPulse). Use when the ticket touches UI AND data/logic layers, or when it involves Streamlit state management, session handling, or deployment. Most ChurnPilot tickets are fullstack.
   - **Backend Engineer** (`backend-architect`) — Pure backend work: CLI tools, API logic, database migrations, test infrastructure, non-UI projects (character-life-sim).
   - **Frontend Engineer** (`frontend-engineer`) — Pure frontend work where no backend changes are needed (CSS-only fixes, static layout changes, pure styling). Rare in Streamlit projects.
   - **Content Engineer** (`content-engineer`) — Marketing content: blog posts, product articles, Reddit/social launch posts, SEO content, documentation updates, README rewrites. Use for any ticket that produces written content rather than code. Has its own overlay with product context and legal constraints (BUILD & SERVE phase).
6. Set `status:in-progress` and spawn the engineer sub-agent
7. **Move on immediately.** Do NOT check if the sub-agent started working. Do NOT verify branch creation. Do NOT re-dispatch in the same session. The precheck stale-ticket detector handles failures automatically.

**Worktree rules for engineers:** Engineers work in an **isolated git worktree** at `/tmp/wt/{repo-short}-{ticket-num}` on branch `fix/{repo-short}-{ticket-num}` (e.g., `/tmp/wt/churn-84` on `fix/churn-84`). They do NOT push to `experiment`. The experiment branch is only touched by QA after code review passes. Code reviewers and QA reuse the same worktree — engineers must NOT remove it.

**Feature tickets:** A ticket's existence IS the CEO's product decision. The CTO owns execution prioritization. Do NOT leave features as `status:new` "awaiting CEO." Only use `status:needs-jj` for genuine unresolved CEO decisions (pricing, legal, strategic pivots).

**Blocked tickets:** If dependencies exist (`### Dependencies` with `#N` refs), query each via GraphQL. If ANY dep is OPEN → set `status:blocked` + comment. Skip dispatch.

**Unblocking is automatic:** A GitHub Action (`unblock-dependencies.yml`) fires when any issue closes. It finds `status:blocked` tickets that depended on it, checks if ALL their deps are now closed, and sets them to `status:new` with a comment. No polling needed.

**Evolver check:**
```bash
workspace/skills/evolver/scripts/signal-extract.sh OWNER REPO ISSUE_NUM | \
  workspace/skills/evolver/scripts/capsule-match.sh
```
If a capsule matches, add "Known Solution Hint" in the ticket comment.

**⛔ CONCURRENCY LIMIT:** Platform allows max 8 concurrent sub-agents (`subagents.maxConcurrent = 8`). Before dispatching, count active agents:
```bash
openclaw sessions list --active 15 --json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
# Count unique cron sessions (exclude :run: children)
agents = [s for s in data.get('sessions', []) if 'cron:' in s.get('key','') and ':run:' not in s.get('key','')]
print(f'Active agents: {len(agents)}/8')
"
```
If at or near the limit (6+), **defer lower-priority dispatches** to the next cycle. Dispatching beyond the limit will silently fail or queue — wasting a CTO session.

**Spawning agents:** Use the dispatch script (NOT `sessions_spawn`):
```bash
bash skills/dispatch-agent/scripts/dispatch.sh \
  --name "eng-sp26-migration" \
  --message "<task prompt with all context>"
```

Options: `--model <alias>` (default: sonnet), `--thinking <level>` (default: medium), `--timeout <sec>` (default: 1200), `--delay <duration>` (default: 1m).

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
2. Add dispatch comment with role, model, and thinking level (e.g., `Dispatching: Code Reviewer (Model: Sonnet, Thinking: Medium)`)
3. Spawn code reviewer to review the **worktree** at `/tmp/wt/{repo-short}-{ticket-num}` (not experiment)
4. Reviewer sets `status:verification` when approved (or `status:new` on rejection)

**Reviewer gate before full review:** If the engineer comment does not explicitly confirm both sync-from-latest-`origin/experiment` and localhost verification on `http://localhost:<port>` (any localhost port is acceptable), reject immediately to `status:new` with the standard incomplete-handoff comment. Do not spend a full review round on code that missed the handoff gate.

**⛔ On rejection:** The reviewer sets `status:new`. The NEXT CTO triage session dispatches an **engineer** to fix the issues — NOT another code reviewer. Sending the same unchanged branch to review again is a dead loop. The flow is always: CR rejects → `status:new` → engineer fixes → `status:review` → new CR. Never: CR rejects → another CR on the same code.

### 3. QA REVIEW
**Trigger:** `status:verification`

**Never skip QA.**

1. Set `status:in-progress` on the ticket (prevents double-dispatch)
2. Add dispatch comment with role, model, and thinking level (e.g., `Dispatching: QA Engineer (Model: Sonnet, Thinking: Medium)`)
3. Spawn QA agent with `qa-overlay.md`

QA responsibilities:
1. Navigate to the shared worktree at `/tmp/wt/{repo-short}-{ticket-num}` — review changes and tests
2. If code and tests look good, **merge the worktree branch into `experiment`** and push
3. Test on the experiment endpoint using browser automation (never localhost)
4. On success: **remove the worktree** (`git worktree remove /tmp/wt/{name} --force` from the main repo dir)
5. On failure: also remove the worktree, then set `status:new`

QA sets `status:cto-review` when passed (or `status:new` on failure).

**⛔ On failure:** Same rule as code review — `status:new` means re-dispatch an **engineer** to fix, not another QA run on the same code.

### 4. CTO REVIEW
**Trigger:** `status:cto-review`

**⛔ PRE-CHECK:** Verify QA Verification Report exists on the ticket. If missing → set `status:verification`.

If QA passed: review the work → if approved → close issue with `status:done`.

**⚠️ After closing: you MUST run metrics recording + shadow evaluation (see below). Do not exit without completing all 3 closure steps.**

**📊 METRICS RECORDING (on every ticket closure):**
When closing a ticket, append one JSON line to EACH of these files:
- `framework/metrics/review-quality.jsonl` — code review quality (already active)
- `framework/metrics/engineer-quality.jsonl` — engineering quality (include `engineer_role`: fullstack/backend/frontend)
- `framework/metrics/qa-quality.jsonl` — QA verification quality
- `framework/metrics/triage-quality.jsonl` — triage/dispatch quality

See `framework/metrics/schemas/metrics-schema.md` for field definitions and score calculation formulas. Use the ticket's GitHub comment history to determine rounds, lint status, QA results, etc. The `trace_id` field (`repo_short#ticket`) links all 4 records for the same ticket.

**📥 RICH INPUT CAPTURE (DSPy training data — include in every metrics record):**
To enable DSPy compilation, each record must also include the actual inputs used. Add these fields alongside the quality metrics:

```json
{
  // ... existing quality fields ...

  // Rich inputs for DSPy training (capture from ticket + git at closure time)
  "dspy_inputs": {
    "ticket_body": "<full GitHub issue body>",
    "diff": "<git diff experiment..branch or summary of changes from engineer comment>",
    "conventions": "<contents of framework/roles/CONVENTIONS.md, truncated to 2000 chars>",
    "lint_output": "<ruff output from engineer/QA comment, or empty string>",
    "streamlit_gotchas": "<contents of framework/knowledge/streamlit-gotchas.md if Streamlit project, else empty>",
    "review_comment": "<the actual CTO/reviewer comment posted to the ticket>",
    "qa_verdict": "<PASS or FAIL from QA report>",
    "verdict": "<APPROVE or REJECT>",
    "dispatch_note": "<triage dispatch comment>",
    "engineer_role": "<fullstack|backend|frontend|content>"
  }
}
```

**How to get the diff:** Check the engineer's completion comment — it usually includes a diff stat or commit hash. If a commit hash is present, run: `git -C projects/[repo]/ show <hash> --stat` to get file changes summary. Use that as `diff`. If unavailable, use `[commit <hash> on experiment branch]`.

**🔬 SHADOW EVALUATION — MANDATORY on every ticket closure:**

⚠️ **DO NOT SKIP THIS STEP.** After recording metrics and closing the issue, you MUST run the shadow evaluation. This is how we measure whether DSPy-optimized prompts are better than baseline. No exceptions — content tickets, code tickets, all tickets.

```bash
# MANDATORY — run this BEFORE exiting the session
exec framework/dspy/shadow-run.sh --stage all --repo OWNER/REPO --ticket TICKET_NUMBER
```

Replace `OWNER/REPO` with the actual repo (e.g., `hendrixAIDev/churn_copilot_hendrix`) and `TICKET_NUMBER` with the issue number (e.g., `162`). This takes ~30-60s and now defaults to `openai/gpt-4.1-mini` unless overridden.

**Checklist for Phase 4 (CTO Review) — all 3 steps required:**
1. ✅ Close the issue with `status:done`
2. ✅ Record metrics to all 4 JSONL files
3. ✅ Run shadow evaluation (command above)

If the shadow script fails (API error, timeout), note it in the daily memory file but do NOT let it block ticket closure. The ticket closure is the priority; shadow is observational but mandatory to attempt.

**To check shadow results:** `framework/dspy/shadow-run.sh --analyze`

**Promotion rule:** When optimized beats baseline on 20+ labeled entries for a stage, the CTO should promote the optimized prompt (update the overlay to use DSPy demos).

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
