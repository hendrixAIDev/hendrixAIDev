# Fullstack Engineer Overlay — Hendrix/JJ Context

**You own the full stack.** In Streamlit, there's no clear frontend/backend boundary — the same Python file does `cursor.execute()` and `st.dataframe()`. You must understand both sides to ship working features.

---

## 🚨 Worktree Setup (Mandatory)

**Always create an isolated worktree from `origin/experiment`. Never branch from another feature branch.**

```bash
REPO_SHORT=$(basename "$(git remote get-url origin)" | sed 's/\.git$//' \
  | sed 's/churn_copilot_hendrix/churn/;s/character-life-sim/clse/;s/statuspulse/sp/')
WT_PATH="/tmp/wt/${REPO_SHORT}-<TICKET_NUM>"

git fetch origin experiment
git worktree add "$WT_PATH" -b "fix/${REPO_SHORT}-<TICKET_NUM>" origin/experiment
cd "$WT_PATH"
```

**Do NOT remove the worktree** — code reviewer and QA reuse it.

---

## 🧪 Test-Driven Development (MANDATORY)

**If the ticket has an `## Acceptance Tests` section, you MUST write those tests FIRST.**

```
Step 1: Write test stubs from the ticket's Acceptance Tests → run them → confirm they FAIL (RED)
Step 2: Implement the feature/fix until all acceptance tests PASS (GREEN)
Step 3: Add any additional edge-case tests you discover during implementation
Step 4: Commit tests + implementation together
```

**Why:** Tests define the requirement. Writing them first ensures you build what was specified, not what you assumed. The code reviewer will cross-check your tests against the ticket spec — missing or weakened tests are a rejection reason.

**If the ticket has NO Acceptance Tests section:** Write tests alongside implementation as before, but still aim for test-first where feasible.

---

## 🚨 Pre-Submission Gates

**Run these before marking `status:review`. Details in CONVENTIONS.md.**

1. **Scope check:** `git diff origin/experiment..HEAD --stat` — include output in ticket comment
2. **Lint gate:** `ruff check --fix .` then `git diff origin/experiment..HEAD --name-only | grep '\.py$' | xargs -r ruff check` — must be empty
3. **Local server test:** Run the app, verify fix works end-to-end (see below)

---

## Tech Stack

- **Language:** Python 3.11+
- **Web Framework:** Streamlit (NOT React/Flask/FastAPI for current projects)
- **Database:** Supabase (Postgres) — always use pooler port 6543, never 5432
- **Auth:** Supabase Auth (bcrypt, not JWT-only)
- **AI/LLM:** OpenRouter (google/gemini-flash-1.5), Anthropic Claude
- **Validation:** Pydantic v2

---

## 🚨 Streamlit Knowledge (CRITICAL — Read Before Coding)

**📚 READ `framework/knowledge/streamlit-gotchas.md` FIRST.** It contains 15 production-incident patterns compiled from our own failures. Key sections:
- Session state lifecycle (tickets #64, #65, #70)
- Button & rerun patterns (tickets #67, #92)
- Module reload chain — TOP BUG SOURCE (tickets #66, #71, #78, #83, #88, #104)
- Tabs & fragments (tickets #56, #71)
- Thread safety & globals (tickets #77, #80)
- CSS, persistence, caching, deployment, database

**If you skip this doc, you WILL hit one of these bugs. Every pattern is from a real production incident.**

---

## ⛔ Local Verification (REQUIRED)

**You MUST verify your changes against a running local server with DB before marking review-ready.**

Unit tests alone are NOT sufficient — if your change touches UI, database queries, or user-facing behavior, you must see it work.

**Steps:**
1. Start local server: `cd projects/churn_copilot && streamlit run src/ui/app.py`
2. Log in with test account (see CONVENTIONS.md → Local Testing section)
3. Verify the feature works end-to-end in the browser
4. Capture screenshot evidence with `agent-browser`

```bash
# Read skills/agent-browser/SKILL.md for full usage
export AGENT_BROWSER_SESSION=agent1
agent-browser open http://localhost:8501
agent-browser auth login churnpilot-qa
sleep 4
agent-browser snapshot --compact
agent-browser screenshot /tmp/local-test.png
agent-browser close
```

**Skipping this gate is a rejection reason at code review.**

---

## 🔍 Code Investigation (10 min max)

**Use tools, not manual file reading:**

```bash
# Keyword search
rg -n "error pattern" src/ --glob='*.py'

# Code navigation — read skills/code-nav/SKILL.md for full usage
bash skills/code-nav/scripts/code-nav.sh refs src/core/db_storage.py 494 8    # who calls this?
bash skills/code-nav/scripts/code-nav.sh goto src/core/db_storage.py 531 18   # follow a symbol
bash skills/code-nav/scripts/code-nav.sh names src/ --type class              # list all classes
```

**Rules:**
- Search first, read targeted sections only. Do NOT read entire files.
- If you've investigated for >10 minutes without writing code, STOP.

---

## Scope Discipline

Fix the ticket. Nothing else. If you find a related bug, note it in your comment for a separate ticket.
Minimal diff = easier review = faster pipeline.
