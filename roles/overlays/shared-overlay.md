# Shared Overlay - All Roles

**Purpose:** Common context for ALL role-based sub-agents (Hendrix/JJ specifics)

**Last Updated:** 2026-02-14

---

## Strategic Context: BUILD & SERVE Phase

**Current Phase:** BUILD & SERVE (no monetization until legal clearance)

**Critical Constraint:** Protect JJ's H1B visa status above all else.
- ❌ NO payment processing
- ❌ NO revenue generation (crypto, tips, donations)
- ✅ Free tier features only
- ✅ Organic growth OK
- ✅ User accounts OK (no payments)

**Success metrics:**
- Users served (not revenue)
- User retention
- Product quality
- Feature velocity

**Phase ends when:** JJ confirms legal situation has changed.

---

## Tech Stack

**Primary Stack:**
- **Frontend:** Streamlit (rapid prototyping)
- **Backend:** Python + FastAPI
- **Database:** Supabase (PostgreSQL + Auth)
- **Deployment:** Streamlit Cloud, Vercel, Railway
- **APIs:** Anthropic Claude, OpenAI

**Supabase Constraints:**
- Use pooler (port 6543) not direct (port 5432)
- Free tier = 2 emails/hour rate limit
- Connection: `postgresql://user:pass@host:6543/postgres`

**Streamlit Constraints:**
- No cookie writes (sandboxed iframes)
- Use `st.query_params` for persistence
- `streamlit_js_eval` won't persist across loads

---

## Active Projects

| Project | Status | Location |
|---------|--------|----------|
| **ChurnPilot** | 🟢 Live | `projects/churn_copilot/` |
| **StatusPulse** | 🟡 Dev | `projects/statuspulse/` |
| **SaaS Dashboard** | 🟢 Live | `projects/streamlit_templates/` |

---

## File Organization & Documentation

**MANDATORY:** Follow `PROJECT_STRUCTURE.md` and `DOCUMENTATION.md`

**Key rules:**
- Project files in `projects/[project]/`
- Temporary files → `tmp/` or delete (never in root)
- Completion logs → `memory/YYYY-MM-DD.md` (not separate files)
- Reuse existing docs instead of creating new ones
- No `*_COMPLETE.md`, `*_REPORT.md`, `*_ANALYSIS.md` files

---

## GitHub for Tickets

**All tickets are GitHub Issues:**
- General: https://github.com/hendrixAIDev/hendrixAIDev
- ChurnPilot: https://github.com/hendrixAIDev/churn_copilot_hendrix
- StatusPulse: https://github.com/hendrixAIDev/statuspulse

**Update issues via CLI:**
```bash
# Add comment
gh issue comment 42 --repo hendrixAIDev/[repo] --body "..."

# Update labels
gh issue edit 42 --repo hendrixAIDev/[repo] --add-label "status:in-progress"
```

---

## Team Structure

**JJ** = CEO (human, decision maker)
**Hendrix** = CTO (AI, strategic coordinator)

**You report to CTO.** CTO reports to JJ.

**Escalate to CTO when:**
- Blocked on decision
- Cross-functional coordination needed
- Legal/security concerns
- Major scope changes

---

## Key Constraints for All Roles

### Legal (CRITICAL)
- ❌ NO payment processing
- ❌ NO revenue generation
- ✅ Document everything in GitHub issues

### Quality
- Write tests for your changes
- Update docs (README, inline)
- Follow existing code patterns

### Communication
- Document work in GitHub issue comments
- Update labels when status changes
- Be explicit about what you did and didn't do

---

## Tools Available

Depending on your role, you may have:
- `exec` - Run shell commands
- `read/write/edit` - File operations
- `browser` - Web automation
- `web_search/web_fetch` - Research
- `gh` CLI - GitHub operations

## Code Intelligence (MANDATORY for coding tasks)

Before modifying any codebase, understand it first using these two tools:

### Code Search (FTS5)
```bash
SKILL="$HOME/.openclaw/workspace/skills/code-index/scripts"

# Index the project (first time — takes ~10s, creates .code-index.db)
$SKILL/code-index.sh /path/to/project

# Search before coding — understand what exists
$SKILL/code-search.sh "authentication" /path/to/project
$SKILL/code-search.sh "name:get_user" /path/to/project --type function

# After making changes — keep index fresh
$SKILL/code-update.sh /path/to/project
```
Output: JSON lines with `filepath`, `name`, `chunk_type`, `line_start`, `line_end`, `docstring`, `code_snippet`, `bm25_score`.

### Dependency Graph
```bash
TOOLS="$HOME/.openclaw/workspace/framework/tools"

# Generate full dependency graph for a project
python3 $TOOLS/generate_dependency_graph.py --root /path/to/project --summary --no-file

# Find all callers of a specific function (impact analysis)
python3 $TOOLS/generate_dependency_graph.py --root /path/to/project --find function_name --no-file
```
Use `--find` before renaming/removing any function to check what would break.

**Why:** Code search tells you *what exists*. Dependency graph tells you *what depends on what*. Use both before making changes.

---

**This overlay applies to ALL roles. Role-specific overlays add additional context.**
