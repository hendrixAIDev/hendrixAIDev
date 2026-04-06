# Shared Overlay - All Roles

**Purpose:** Common context for ALL role-based sub-agents

**Last Updated:** 2026-03-01


## Tech Stack

**Primary Stack:**
- **Frontend:** Streamlit (rapid prototyping)
- **Backend:** Python + FastAPI
- **Database:** Supabase (PostgreSQL + Auth)
- **Deployment:** Streamlit Cloud, Vercel, Railway
- **APIs:** Anthropic Claude, OpenAI

**Supabase Constraints:**
- Use pooler (port 6543) not direct (port 5432)
- Connection: `postgresql://user:pass@host:6543/postgres`

**Streamlit Constraints:**
- No cookie writes (sandboxed iframes)
- Use `st.query_params` for persistence
- `streamlit_js_eval` won't persist across loads

**Streamlit Browser Testing (agent-browser):**
- **⚠️ CRITICAL — `/~/+/` path for Streamlit Cloud only:** `agent-browser open https://app.streamlit.app/~/+/` — NOT the bare domain. The root URL loads a Streamlit Cloud wrapper with a cross-origin iframe — `snapshot` returns only 2 elements. `/~/+/` goes straight to the app. **For localhost, do NOT use `/~/+/`** — just `http://localhost:8501` (there's no iframe wrapper locally).
- **⚠️ Sleeping apps — 303 redirect to auth is NOT an auth issue:** Streamlit Cloud free tier hibernates apps after ~7 days of no traffic. When sleeping, ALL requests (including `/_stcore/health`) return HTTP 303 → `share.streamlit.io/-/auth/app`. This looks like auth but is actually a sleep redirect. Fix: navigate to the app URL with `agent-browser`, look for a "Wake app" button in the snapshot, click it, then wait 30–60s for boot before testing. If it persists, reboot the app from Streamlit Cloud dashboard.
- **Auth:** Use `agent-browser auth login churnpilot-qa` (credentials pre-saved on host). No need to fill login forms manually.
- **Session isolation:** Set `export AGENT_BROWSER_SESSION=agent1` once at the top of your script — all subsequent commands inherit it automatically.
- **Cleanup:** Always `agent-browser close` when done — instant, no hanging processes.

---

## Active Projects

See `framework/PROJECTS.md`

## File Organization & Documentation

**MANDATORY:** Follow `PROJECT_STRUCTURE.md`

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
- CharacterLifeSim: https://github.com/hendrixAIDev/character-life-sim

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
- `web_search/web_fetch` - Research
- `gh` CLI - GitHub operations
- `grep` - general search

## Available Skills

These skills are installed in the workspace. Read the SKILL.md file (just the header) when you need one:

- **agent-browser** (`skills/agent-browser/SKILL.md`): Browser automation CLI for AI agents — navigating pages, filling forms, clicking buttons, taking screenshots, testing web apps.
- **code-nav** (`skills/code-nav/SKILL.md`): Python code navigation — goto-definition, find-references, list-names using jedi. Use BEFORE modifying code to understand call chains and impact.
- **gh-screenshot** (`skills/gh-screenshot/SKILL.md`): Upload screenshots to GitHub issue comments as inline images.
- **online-search** (`skills/perplexity/SKILL.md`): Perplexity online search.

---

**This overlay applies to ALL roles. Role-specific overlays add additional context.**
