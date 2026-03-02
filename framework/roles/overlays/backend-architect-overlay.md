# Backend Engineer Overlay - Hendrix/JJ Context

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

## 🚨 Pre-Submission Gates

**Run these before marking `status:review`. Details in CONVENTIONS.md.**

1. **Scope check:** `git diff origin/experiment..HEAD --stat` — include output in ticket comment
2. **Lint gate:** `ruff check --fix .` then `git diff origin/experiment..HEAD --name-only | grep '\.py$' | xargs -r ruff check` — must be empty
3. **Local server test:** Run the app, verify fix works end-to-end (see CONVENTIONS.md)

---

## Tech Stack

- **Language:** Python 3.11+
- **Web:** Streamlit (not FastAPI/Flask for current projects)
- **Database:** Supabase (Postgres) — always use pooler port 6543, never 5432
- **Auth:** Supabase Auth (bcrypt, not JWT-only)
- **AI/LLM:** OpenRouter (google/gemini-flash-1.5), Anthropic Claude
- **Validation:** Pydantic v2

## Key Constraints

- **Supabase pooler:** Connection string must use port 6543
- **No direct DB writes in tests** — use app layer, never raw SQL
- **`@st.cache_resource` not `@st.cache_data`** for Pydantic models / non-serializable types
- **Module reload chain:** If you add/move `src/core/` imports, update `_RELOAD_MODULES` in `app.py` (see CONVENTIONS.md)

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

## 🔍 Local Verification with Browser

After local server testing, use `agent-browser` to capture evidence:

```bash
# Read skills/agent-browser/SKILL.md for full usage
export AGENT_BROWSER_SESSION=agent1
agent-browser open http://localhost:8501/~/+/
agent-browser auth login churnpilot-qa
sleep 4
agent-browser snapshot --compact
agent-browser screenshot /tmp/local-test.png
agent-browser close
```

---

## Scope Discipline

Fix the ticket. Nothing else. If you find a related bug, note it for a separate ticket.
Minimal diff = easier review = faster pipeline.
