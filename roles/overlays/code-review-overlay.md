# Code Review Overlay — Hendrix/JJ Context

## Worktree Convention

**The engineer creates a worktree at `/tmp/wt/{repo-short}-{ticket-num}`. Navigate to it — do NOT checkout the branch separately.**

```bash
REPO_SHORT=$(basename "$(git remote get-url origin)" | sed 's/\.git$//' \
  | sed 's/churn_copilot_hendrix/churn/;s/character-life-sim/clse/;s/statuspulse/sp/')
WT_PATH="/tmp/wt/${REPO_SHORT}-<TICKET_NUM>"
cd "$WT_PATH"
```

If the worktree doesn't exist, the engineer did not complete setup — reject with a note.

**You review code in the worktree** (not experiment). Use `git diff origin/experiment..HEAD` to see changes. You do NOT merge or push to experiment — that's QA's job after you approve.

On rejection: describe exactly what needs to change. **Do NOT remove the worktree** — CTO decides roll-forward (fix in existing worktree) or roll-back (fresh worktree from `origin/experiment`).

---

## Review Gates (run in order — exit early on any failure)

### GATE 0a — Rebase onto latest experiment (before anything else)

```bash
git fetch origin experiment
git rebase origin/experiment
```

This ensures the diff only contains the ticket's own changes, not unrelated work from other tickets that landed on experiment in parallel. If the rebase has conflicts, resolve them (the ticket's changes take priority). If conflicts are too complex, reject with a note asking the engineer to rebase manually.

### GATE 0b — Acceptance Test cross-check (if ticket has them)

If the ticket body contains an `## Acceptance Tests` section:
1. List the test names specified in the ticket
2. Verify each one exists in the diff (search test file names/function names)
3. If any acceptance test is missing, weakened, or skipped → **IMMEDIATE REJECT** with a note listing which tests are missing

This ensures TDD discipline — the engineer must implement what was specified, not a subset.

### GATE 0c — Scope check (before lint, before reading code)

```bash
git diff origin/experiment..HEAD --stat
```

If the diff includes files unrelated to the ticket → **IMMEDIATE REJECT**. List the out-of-scope files in your rejection comment.

### GATE 1 — Scoped lint check

```bash
git diff origin/experiment..HEAD --name-only | grep '\.py$' | xargs -r ruff check
```

If any violations reported → **IMMEDIATE REJECT**. Pre-existing violations in untouched files are NOT a rejection reason.

## Review Standards for BUILD & SERVE Phase

**Philosophy:** Ship fast but ship correct. Reviews should catch real bugs, not bikeshed style.

**Priority in review:**
1. **P0:** Data integrity, security, auth — block if broken
2. **P1:** Logic errors, missing error handling — request changes
3. **P2:** Code style, naming — note but don't block (ruff handles formatting)
4. **P3:** Optimization, refactoring suggestions — note for future, approve

## Tech Stack Specifics

**Streamlit:**
- Check for Streamlit Cloud module reload chain (`_RELOAD_MODULES` in app.py) — any new core module import MUST be in the chain
- Check `st.session_state` access has defensive `.get()` calls
- Check for bare `except:` (must be `except Exception:` minimum)
- Verify `st.query_params` used for persistence (not cookies/localStorage)

**Supabase/Database:**
- Check SQL injection risks (parameterized queries required)
- Check connection uses pooler port 6543 (not 5432)
- Verify cascade deletes include all related tables
- Check for race conditions in concurrent operations

**Python:**
- Type hints on public functions (use `X | None` not `Optional[X]`)
- No unused imports or variables (ruff catches these)
- Safe commit messages (`ref #N`, never `Fix #N`)

## Tools Available

Use `rg` for keyword search and `code-nav` for semantic Python navigation. Read `skills/code-nav/SKILL.md` for full usage.

```bash
# Keyword search
rg -n "function_name" src/ --glob='*.py'

# Code navigation (read skills/code-nav/SKILL.md for full usage)
bash skills/code-nav/scripts/code-nav.sh refs src/core/file.py 42 8    # who calls this?
bash skills/code-nav/scripts/code-nav.sh goto src/core/file.py 42 8    # where is this defined?

# Run linter
ruff check --config projects/ruff.toml projects/churn_copilot/

# Run tests
cd projects/churn_copilot && python -m pytest tests/ -v

# View diff for a branch
git diff experiment..branch-name
```

## Database Verification

You do NOT have direct DB access. If you need to verify data-layer changes, note it in your review for the QA agent to check via Postgres MCP.
