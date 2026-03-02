# Role Conventions - All Roles Must Follow

**Purpose:** Generic instructions that apply to ALL role-based sub-agents.

**Last Updated:** 2026-02-18

---

## 🗂️ MANDATORY: Dependency Graph Workflow (for Code-Modifying Agents)

**Context:** Sub-agents have missed cross-file implications when modifying code, causing cascading failures (e.g., Issue #62: moved `go_to_add_card()` but 3 test files still imported from old location → 16 test failures, wasted QA cycles).

**Tools:** Code search and dependency graph are documented in the shared overlay (`shared-overlay.md` → "Code Intelligence" section). All sub-agents receive these instructions automatically.

**Do NOT commit DEPENDENCY_GRAPH.json to git** — regenerate fresh each session.

### Why This Matters

| Without Graph | With Graph |
|--------------|------------|
| Move function → forget to update 3 test imports | See all 3 callers before moving |
| Change module path → 16 test failures | Update all importers first |
| Rename class → QA cycle wasted | Know all 29 files that import it |

---

## 🔍 Code Navigation — Understand Before You Modify

Before modifying any code, **search and navigate the codebase** to understand context:

```bash
# Keyword search (grep — any language, always fresh)
rg -n "save_card" src/ --glob='*.py'

# Code navigation (goto-definition, find-references — Python)
# Read the code-nav skill (skills/code-nav/SKILL.md) for full usage
# Read skills/code-nav/SKILL.md for full usage
bash skills/code-nav/scripts/code-nav.sh refs src/core/db_storage.py 494 8    # who calls save_card?
bash skills/code-nav/scripts/code-nav.sh goto src/core/db_storage.py 531 18   # follow a symbol
bash skills/code-nav/scripts/code-nav.sh names src/ --type class              # list all classes
```

**Combined workflow:**
1. **grep/rg** → find relevant files and lines
2. **code-nav refs** → check what depends on what you're changing
3. **Read the specific sections** → understand the implementation
4. **Make changes** → with full context

---

## 📖 Required Reading - BEFORE You Start

**Before doing ANY work on a ticket, read these files in order:**

1. **PROJECT_STRUCTURE.md** (workspace root)
   - Where files belong (root vs projects/ vs tmp/)
   - Temporary vs permanent files
   - Daily memory vs long-term memory (MEMORY.md)
   - Where reports/analysis go (hint: NOT in docs/)
   - Reuse rule and cleanup checklist

1b. **projects/PROJECT_STANDARDS.md**
   - Linting & formatting requirements (ruff, mypy, pre-commit)
   - New project checklist
   - Code style and testing requirements
   - **Your code MUST pass `ruff check` before marking QA-ready**

2. **TICKET_SYSTEM.md** (`framework/board-review/TICKET_SYSTEM.md`)
   - GitHub workflow, labels, status transitions
   - How to create/update tickets via `gh` CLI
   - Slack summary format (with links)
   - **Critical:** Only CTO closes issues

3. **ISSUE_COMPLETION_TEMPLATE.md** (`framework/board-review/ISSUE_COMPLETION_TEMPLATE.md`)
   - **READ THIS BEFORE FINISHING WORK**
   - Completion checklist
   - Correct commands to update issue status
   - Comment template for completion
   - **⛔ CRITICAL: Explains why you must NOT close issues yourself**

4. **CONVENTIONS.md** (this file)
   - How to document your work in tickets
   - Testing requirements (fix = tested, not just code changed)
   - File organization rules
   - Status transitions

**If you skip these, you WILL violate workflow rules.**

---

## ⛔ Database Access Rules

**Postgres MCP** (`mcporter call postgres.*`) is available for **QA agents only**.

| Tool | Allowed | Who |
|------|---------|-----|
| `postgres.query` (SELECT) | ✅ | QA agents only |
| `postgres.list_tables` | ✅ | QA agents only |
| `postgres.describe_table` | ✅ | QA agents only |
| `postgres.execute` (INSERT/UPDATE/DELETE) | ❌ **NEVER** | Nobody |
| `postgres.connect_db` | ❌ | Not needed (auto-connects) |

**Backend engineers:** Do NOT use the Postgres MCP. Use your application's database layer (psycopg2, SQLAlchemy, etc.) for testing.

**CTO:** Do NOT query the database directly. Instruct QA agents to verify data and include results in their QA report.

**Why these restrictions:** The MCP connection uses the main database credentials (not read-only). The read-only restriction is enforced by convention, not by the server. Violating this could corrupt production data.

---

## ⚠️ Streamlit Cloud Module Reload Chain

**If you add or modify imports in any `src/core/` module**, you MUST verify the reload chain in `src/ui/app.py`.

Streamlit Cloud hot-reloads `app.py` on deploy but keeps imported modules cached in `sys.modules`. The `_RELOAD_MODULES` list in `app.py` forces specific modules to reload. If your module isn't in this list, Streamlit Cloud will use the **old cached version**, causing import errors or stale behavior.

**Check this list whenever you:**
- Add a new class/function to an existing core module that other modules import
- Create a new `src/core/*.py` module
- Change import relationships between core modules

**Past incidents:** #66, #71, #78 — all caused by modules missing from the reload chain.

```python
# In src/ui/app.py — add your module here if needed:
_RELOAD_MODULES = [
    "src.core.exceptions",   # Layer 0
    "src.core.database",     # Layer 1
    "src.core.models",
    "src.core.db_storage",
    "src.core.periods",      # Layer 2
    "src.core.optimistic",
    ...
]
```

---

## ⚠️ COMMIT MESSAGE RULES

**NEVER use these keywords in commit messages — they AUTO-CLOSE issues:**
- ❌ `Fix #54` / `Fixes #54` / `Fixed #54`
- ❌ `Close #54` / `Closes #54` / `Closed #54`
- ❌ `Resolve #54` / `Resolves #54` / `Resolved #54`

**USE these safe patterns instead:**
- ✅ `Implement SCHP endpoint (ref #54)`
- ✅ `Add health capabilities - relates to #54`
- ✅ `[#54] Add SCHP endpoint implementation`

**Why:** GitHub auto-closes issues when these keywords are used. This bypasses our QA → CTO review workflow.

---

## 🔴 MANDATORY: Document Your Work in the Ticket

**As you work on a ticket, continuously update the Implementation Log.**

### Why This Matters

- ✅ QA can see exactly what you implemented
- ✅ CTO can review your approach and decisions
- ✅ Other agents can pick up where you left off
- ✅ Creates audit trail for debugging
- ✅ Helps future agents learn from your work

### When to Update the Ticket

**Update the ticket's Implementation Log:**
- When you START working (note your approach)
- When you make KEY DECISIONS (and why)
- When you COMPLETE significant steps
- When you encounter BLOCKERS
- When you FINISH (final summary)

### Format for Updates

Add entries to the ticket's `## Implementation Log` section:

```markdown
### YYYY-MM-DD HH:MM — [Brief Title]
**Agent:** [Your Role] (session: [your session key if known])
**Status:** [IN PROGRESS | BLOCKED | QA_REVIEW | etc.]

**What I did:**
- [Action 1]
- [Action 2]

**Decisions made:**
- [Decision and reasoning]

**Files changed:**
- `path/to/file.py` - [what changed]
- `path/to/test.py` - [what changed]

**Tests:**
- [Test results, pass/fail]

**Next steps:**
- [What needs to happen next]

**Blockers (if any):**
- [Blocker description]

---
```

### Example: Backend Engineer Working on Auth Fix

```markdown
### 2026-02-14 15:45 — Started Implementation
**Agent:** Backend Engineer (session: be-abc123)
**Status:** IN PROGRESS

**What I did:**
- Read the ticket requirements
- Analyzed current auth flow in `src/auth/login.py`
- Identified the timeout issue (line 47, hardcoded 5s timeout)

**Approach:**
- Will make timeout configurable via environment variable
- Default to 30s, allow override via AUTH_TIMEOUT_SECONDS

**Next steps:**
- Implement the fix
- Add unit tests
- Update documentation

---

### 2026-02-14 16:00 — Implementation Complete
**Agent:** Backend Engineer (session: be-abc123)
**Status:** QA_REVIEW

**What I did:**
- Changed timeout to configurable (default 30s)
- Added AUTH_TIMEOUT_SECONDS env var support
- Added 3 unit tests for timeout scenarios

**Files changed:**
- `src/auth/login.py` - Made timeout configurable
- `tests/test_auth.py` - Added timeout tests
- `docs/CONFIGURATION.md` - Documented new env var

**Tests:**
- All 3 new tests passing
- Existing 12 auth tests still passing
- Total: 15/15 passing

**Ready for QA.**

---
```

---

## 📖 Read Before You Write

**Before making changes:**

1. **Read the ticket thoroughly** - Understand requirements and success criteria
2. **Read existing code** - Understand what's already there
3. **Read related docs** - Check for constraints or conventions
4. **Read PROJECT_STRUCTURE.md** - Know where files belong

**Don't jump into coding without understanding context.**

---

## 🧪 Test Your Work

**⚠️ CRITICAL: "Fixed" means TESTED, not just "code changed"**

**A fix is NOT complete until you have:**

1. ✅ **Written a test that reproduces the bug** (fails before your fix)
2. ✅ **Verified the test passes with your fix** (confirms fix works)
3. ✅ **Run existing tests** (don't break what already works)
4. ✅ **🚨 TESTED ON LOCAL SERVER** (Streamlit, API, browser)
5. ✅ **Documented test results in ticket** (proof you tested)

**Never say "fix verified" without actual test evidence.**

**Bad:** "I committed the fix, it should work now" ❌  
**Good:** "Added test_psycopg2_uuid_cast() - fails on main, passes on my branch. Manual test on local server: loaded dashboard with 25 cards, no errors." ✅

### 🚨 MANDATORY: Test on Local Server

**If your fix involves UI, API, or user-facing functionality:**

You **MUST** test it on the local server before marking QA-ready.

**Why this matters:**
- ✅ Catches issues early (faster iteration than waiting for deployment)
- ✅ Verifies code actually works in real app context (not just unit tests)
- ✅ Prevents QA from finding "feature doesn't exist" issues
- ✅ Saves time (no deployment wait, no back-and-forth with QA)

**Workflow for Implementation Engineers:**
```
Write Code → Unit Tests → Local Server Test → Mark QA-Ready
```

**How to test locally:**

1. **Start the local server:**
   ```bash
   cd projects/churn_copilot/app
   source venv/bin/activate
   streamlit run src/ui/app.py
   ```

2. **Open in browser:** `http://localhost:8501`

3. **Login with test account:**
   - Email: `automation@churnpilot.test`
   - Password: `AutoTest2024!`

4. **Verify your fix actually works:**
   - [ ] Feature is visible (UI elements appear where expected)
   - [ ] Feature is functional (buttons work, forms submit, etc.)
   - [ ] No console errors (check browser dev tools)
   - [ ] Tested edge cases (errors, empty data, etc.)

5. **Document local testing in ticket:**
   ```markdown
   **Local Testing:**
   - ✅ Tested on local server (http://localhost:8501)
   - ✅ Logged in with automation@churnpilot.test
   - ✅ Verified toggle button visible in top-left corner
   - ✅ Tested toggle functionality (hide/show sidebar)
   - ✅ Tested edge case: toggle persists after page refresh
   - ✅ No console errors
   ```

**📚 Full guide:** See `projects/churn_copilot/app/docs/LOCAL_TESTING_GUIDE.md`

**Real example of what NOT to do:**
- ❌ "Unit tests pass, should work" (didn't run actual app)
- ❌ Result: QA found toggle button completely missing from page
- ❌ Wasted: QA cycle, CTO review time, re-assignment to frontend engineer

**Before marking QA_REVIEW:**

- [ ] Tests written for your changes (unit or integration)
- [ ] Tests pass locally: `make test-unit`
- [ ] Existing tests still pass (no regressions)
- [ ] **🚨 Tested on local server** (feature actually works in running app)
- [ ] Test results documented in ticket log

**After you mark QA-ready:**
- QA Engineer tests on `experiment` endpoint (deployed environment)
- QA validates your implementation meets acceptance criteria
- This is the proper division of labor: **you test locally, QA tests deployed**

**QA Engineers MUST verify fixes on the deployed experiment endpoint, NOT localhost.**

**Experiment endpoint:** `https://churncopilothendrix-bc5b56cmnopm2ixz3dvhwd.streamlit.app`

**QA Verification Steps (MANDATORY):**
1. Open experiment endpoint in browser (use browser tool)
2. Login with test account
3. Navigate to the affected feature
4. Verify the fix works in the deployed environment
5. Take browser snapshot as evidence
6. Document: "Tested on experiment endpoint ✅" (not just "Tested locally")

**If experiment endpoint is inaccessible:** Label `status:needs-jj`, do NOT pass QA.

> _Added per CEO directive (Feb 19, 2026) — Issue #69 was closed as "fixed" based on localhost testing only, but the fix did not work on the experiment endpoint._

**If you can't test locally, explain why in the ticket and flag for CTO assistance.**

---

## 📁 File Organization & Documentation

**MANDATORY:** Read `DOCUMENTATION.md` for complete rules.

**Quick reference:**
- **Temporary files** → `tmp/` or delete (never in root/project root)
- **Completion logs** → `memory/YYYY-MM-DD.md` (not separate files)
- **Reuse existing files** → Don't create new files for same topic
- **Never create** → `*_COMPLETE.md`, `*_REPORT.md`, `*_ANALYSIS.md`

**Before creating any file, ask:**
1. Does a file for this topic exist? → Update it
2. Is this a completion event? → Add to daily memory
3. Is this temporary? → Put in `tmp/` or delete after
4. Will this be useful in 30 days? → If no, don't create

### Appending to Daily Memory Files

**⚠️ IMPORTANT:** Do NOT use `---` as anchor text for edits - it appears many times!

**Correct approach to append to `memory/YYYY-MM-DD.md`:**

```python
# 1. Read the file to find unique anchor text
read(path="memory/2026-02-16.md", offset=-20)  # Read last 20 lines

# 2. Find the LAST unique heading (e.g., "## 11:44 AM - Board Review")
# Use that heading + some unique content as anchor

# 3. Or simply append by reading entire file and writing back
# This is safer than using edit with non-unique text
```

**Never use these as anchor text (not unique):**
- `---` (horizontal rule - appears many times)
- `**Next cycle:**` (common phrase)
- Generic timestamps without context

**Always use these patterns:**
- Full heading: `## 11:44 AM - Board Review Cycle (CTO)`
- Unique content from last entry
- Or read full file and write with new content appended

---

## 🚫 Don't Assume - Ask or Document

**If you encounter ambiguity:**

1. **Check existing docs** - Answer might be there
2. **Make a reasonable decision** - Document your reasoning in the ticket
3. **Flag for review** - Note it in the ticket so CTO/QA can verify

**Bad:** Silently making assumptions
**Good:** "Assumed X because Y. Flagging for CTO review."

---

## 🔄 Status Transitions

**When changing ticket status:**

| From | To | When |
|------|----|----|
| `status:new` | `status:in-progress` | CTO triages and dispatches engineer |
| `status:in-progress` | `status:review` | Engineer done → ready for code review |
| `status:review` | `status:in-progress` | CTO dispatches code reviewer |
| `status:in-progress` | `status:verification` | Code review passes |
| `status:in-progress` | `status:new` | Code review rejects (with feedback) |
| `status:verification` | `status:in-progress` | CTO dispatches QA |
| `status:in-progress` | `status:cto-review` | QA merges to experiment + tests pass |
| `status:in-progress` | `status:new` | QA fails (with feedback) |
| `status:cto-review` | `status:done` (CLOSED) | CTO approves |
| `status:cto-review` | `status:new` | CTO rejects |
| Any | `status:needs-jj` | CTO needs CEO decision (Phase 1 only) |

**Always update labels via GitHub CLI and add comment explaining status change.**

---

## 🚨 When You're Stuck: Use `status:needs-jj`

**If you encounter a blocker only JJ can resolve:**

1. **Stop working** (don't waste time on impossible task)
2. **Document what you tried** in GitHub comment
3. **Set label to `status:needs-jj`**
4. **Explain clearly what JJ needs to do**

**Examples of `status:needs-jj` situations:**
- Need JJ's credentials/access
- Legal/financial decision required
- Feature clarification from JJ (he requested it)
- Multiple failed attempts (you're the 2nd+ agent on this ticket)
- Production-only issue (can't reproduce in test environment)

**Template for `status:needs-jj` comment:**
```markdown
### Needs JJ's Attention

**Reason:** [Brief explanation]

**What I tried:**
- [Attempt 1]
- [Attempt 2]
- [Result]

**Blocker:**
[Specific thing preventing progress]

**What JJ needs to do:**
1. [Action 1]
2. [Action 2]

**Then I can:** [What you'll do after JJ unblocks]
```

---

## 🔄 Engineer → Code Review Handoff

**When your engineering work is complete and tested locally:**

Set `status:review` to trigger the next phase. **Stay on your local feature branch — do NOT push to experiment.**

**Steps:**
```bash
# 1. Set status:review (triggers CTO to dispatch code reviewer)
gh issue edit <number> --repo hendrixAIDev/<repo> \
  --remove-label "status:in-progress" \
  --add-label "status:review"

# 2. Post completion comment (see template below)
# 3. LEAVE ISSUE OPEN
```

**Pipeline flow:** Engineer (local branch) → Code Review (local branch) → QA (local branch → experiment) → CTO
- Precheck detects `status:review` → triggers CTO → CTO dispatches code reviewer
- Code review passes → `status:verification` → CTO dispatches QA
- QA merges to experiment, tests on experiment endpoint → `status:cto-review`
- Code review fails → `status:new` with feedback → engineer reworks

**What NOT to do:**
- ❌ Push to `experiment` (only QA does this)
- ❌ Set `status:verification` or `status:cto-review` yourself
- ❌ Close the issue

---

## 🚨 CRITICAL: Never Close Issues Yourself

**ONLY CTO closes issues.**

**When you finish your work:**
- ✅ Flip role to `role:review` and set `status:assigned` (triggers code review pipeline)
- ✅ Post final comment with summary
- ✅ **LEAVE ISSUE OPEN**

**What NOT to do:**
- ❌ Close the issue (even if you think it's done)
- ❌ Set label to `status:done` (CTO does this)
- ❌ Mark as complete without review

**Why:**
- Closing issue = bypassing QA_REVIEW and CTO_REVIEW phases
- CTO needs to verify your work meets acceptance criteria
- QA watchdog needs to validate tests
- Only CTO has the full context to approve closure

**Workflow enforcement:**
```
YOU: Fix → Test → Comment → Label "status:qa-review" → LEAVE OPEN
QA WATCHDOG: Validate tests → Label "status:cto-review"
CTO: Review → Approve → Deploy to `experiment` → CLOSE ISSUE
CEO: Test on `experiment` → Approve merge to `main` (production)
```

**If you close an issue prematurely, CTO will reopen it for review.**

---

## 🚀 Deployment & Merge Authorization

**CTO closes tickets. CEO authorizes production merges.**

**Deployment Workflow (for deployable projects like ChurnPilot):**

1. **Engineer implements fix** → Works on **local feature branch** (e.g., `fix/cp84-benefits-sync`)
2. **Code Reviewer reviews** → Reviews code on the local branch
3. **QA Engineer reviews tests** → Reviews unit/E2E tests on the local branch
4. **QA Engineer merges to `experiment`** → Merges local branch into `experiment` and pushes
5. **QA Engineer tests on experiment** → Browser automation on experiment endpoint
6. **CTO reviews & closes ticket** → Verifies QA report, closes issue
7. **CEO tests on `experiment`** → Verifies production readiness
8. **CEO authorizes merge to `main`** → Only CEO can approve production deployment

**Authority Boundaries:**

| Action | Authority |
|--------|-----------|
| Work on local feature branch | Engineer |
| Review code on local branch | Code Reviewer |
| Merge to `experiment` + test | QA Engineer |
| Close tickets | CTO (Hendrix) |
| Technical decisions | CTO (Hendrix) |
| **Merge to `main`** | **CEO (JJ) ONLY** |
| Legal/financial decisions | CEO (JJ) ONLY |
| Strategic direction | CEO (JJ) ONLY |

**When closing a ticket, CTO should note:**
> "QA verified on `experiment`. Ticket closed. **Ready for CEO testing on experiment endpoint. Awaiting CEO approval for merge to `main`.**"

**Never say:**
- ❌ "Approved for merge to main" (only CEO approves)
- ❌ "Merged to main" (without CEO authorization)

**Always say:**
- ✅ "Deployed to `experiment`, ready for CEO review"
- ✅ "Awaiting CEO approval for production merge"

---

## 💬 Communication

**How to communicate with other agents:**

1. **Via ticket log** - Primary method (document everything)
2. **Via sessions_send** - If CTO needs to message you
3. **Via BLOCKED status** - If you need escalation

**You are NOT in direct contact with other agents.** The ticket is your communication channel.

---

## ⏱️ Time Management

**Sub-agent timeouts:** Usually 30 minutes (1800 seconds)

**If you're running out of time:**
1. Document what you've done so far
2. Note what's remaining
3. Set status to IN PROGRESS (not QA_REVIEW)
4. Next agent can continue where you left off

**Don't leave work undocumented just because you ran out of time.**

---

## 🎯 Success Criteria Checklist

**Before marking QA_REVIEW:**

1. [ ] Read success criteria from ticket
2. [ ] Verify EACH criterion is met
3. [ ] Document how each was verified (in log)
4. [ ] Update status to QA_REVIEW

**If a criterion can't be met:**
- Document why
- Suggest alternatives
- Flag for CTO decision

---

## 📋 Handoff to QA

**When you mark QA_REVIEW, QA needs to know:**

- What you implemented (summary)
- Files changed (list them)
- How to test (steps or commands)
- Any concerns or edge cases
- Test results (what you already verified)

**Put all this in your final log entry.**

---

## Quick Reference

**Every ticket update should include:**
- Timestamp
- Your role + session
- Current status
- What you did
- What's next

**Every implementation should include:**
- Code changes documented
- Tests written/run
- Docs updated
- Success criteria verified

**Every handoff should include:**
- Summary of work
- Files changed
- How to verify
- Any concerns

---

## 🚀 Deploy Smoke Test Verification

**Post-deploy smoke tests gate both experiment and production deploys.** The smoke test runs automatically in the board review pipeline (see `BOARD_REVIEW.md` Phase 4 and Phase 5).

### How It Works

The smoke test script (`framework/tools/smoke_test.py`) checks:

1. **Tier 1 — Liveness:** Hits Streamlit's built-in `/_stcore/health` endpoint to confirm the app is running
2. **Tier 2 — SCHP (browser only):** Parses `?health=capabilities` for DB status, auth, version info

### When It Runs

| Gate | When | What Happens on Failure |
|------|------|------------------------|
| **Pre-QA** (Phase 4) | Before spawning QA agent | Ticket → `status:needs-jj`, Slack alert |
| **Post-Push** (Phase 5) | After CTO pushes to `experiment` | Slack alert, ticket NOT closed |
| **Production** (Phase 5) | After CEO-authorized merge to `main` | 🚨 Slack alert, immediate investigation |

### Parameters

- **Retries:** 3 attempts at 60-second intervals
- **Timeout:** 30 seconds per request
- **Endpoints:**
  - Experiment: `https://churncopilothendrix-bc5b56cmnopm2ixz3dvhwd.streamlit.app`
  - Production: `https://churnpilot.streamlit.app`

### Manual Usage

```bash
# Test experiment endpoint
python3 framework/tools/smoke_test.py --env experiment

# Test production endpoint
python3 framework/tools/smoke_test.py --env production

# Test with expected SHA verification
python3 framework/tools/smoke_test.py --env experiment --expected-sha a1b2c3d

# Single attempt (no retries)
python3 framework/tools/smoke_test.py --env experiment --single

# Custom URL
python3 framework/tools/smoke_test.py --url http://localhost:8501 --single
```

### Version Info

The health endpoint now includes version info (git SHA, branch, deploy timestamp).
Generate `version.json` before deploy:

```bash
cd projects/churn_copilot/app
python3 scripts/generate_version.py
```

This creates `src/core/version.json` which the health endpoint reads automatically.

### Viewer Auth Requirement

⚠️ **The smoke test requires the Streamlit app to be public** (Settings → Sharing → Public in Streamlit Cloud). If viewer auth is enabled, the smoke test will detect it and report `VIEWER_AUTH_BLOCKED`. The app has its own authentication (bcrypt login), so making it public doesn't expose user data.

---

**This is how we maintain quality and coordination across autonomous agents.**
