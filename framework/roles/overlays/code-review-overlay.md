# Code Review Overlay — Hendrix/JJ Context

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

Code search + dependency graph are in the shared overlay ("Code Intelligence" section). Additionally for reviews:

```bash
# Run linter
ruff check --config projects/ruff.toml projects/churn_copilot/

# Run tests
cd projects/churn_copilot/app && python -m pytest tests/ -v

# View diff for a branch
git diff experiment..branch-name
```

## Database Verification

You do NOT have direct DB access. If you need to verify data-layer changes, note it in your review for the QA agent to check via Postgres MCP.
