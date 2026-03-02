# Frontend Engineer Overlay - Hendrix/JJ Context

**Our frontend is Streamlit.** Ignore the React/Vue/Angular expertise in the base role — adapt those principles to Streamlit's paradigm.

---

## 🚨 Streamlit-Specific Knowledge (CRITICAL)

### Execution Model
- Streamlit re-runs the **entire script** on every interaction (button click, input change, rerun)
- State persists ONLY via `st.session_state` — local variables reset every run
- Guard expensive operations with `@st.cache_resource` or `@st.cache_data`

### Module Reload Chain (Top Bug Source)
- Streamlit Cloud hot-reloads modules, but **not all of them** unless explicitly listed
- `_RELOAD_MODULES` in `app.py` controls which modules get reloaded
- **If you add a new `src/core/` module or change imports, add it to `_RELOAD_MODULES`**
- Past incidents: #66, #71, #78, #88, #104 — ALL caused by missing reload chain entries
- Symptom: "works locally, fails on Cloud" or Pydantic validation errors after deploy

### Session State Patterns
```python
# ✅ Defensive access (always)
value = st.session_state.get("key", default)

# ❌ Direct access (crashes on first run)
value = st.session_state["key"]

# ✅ Initialize early, check often
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.page = "home"
```

### Navigation & Page State
```python
# ✅ Use query params for page persistence (survives reload)
st.query_params["page"] = "dashboard"

# ❌ Cookies — sandboxed iframe, can't write
# ❌ localStorage — iframe-scoped, won't persist across loads
# ❌ st.session_state alone — lost on page refresh
```

### Callbacks & Buttons
```python
# ✅ on_click with callback (processes before rerun)
st.button("Save", on_click=save_handler, args=(data,))

# ❌ if st.button() then do_work() — work runs AFTER rerun starts
# This causes "click → page disappears → need to click again" bugs
# Past incidents: #98, #105, #108
```

### Caching Rules
```python
# ✅ @st.cache_resource — for DB connections, Pydantic models, non-serializable objects
# ✅ @st.cache_data — for serializable data (DataFrames, dicts, lists)
# ❌ @st.cache_data with Pydantic models — fails silently or causes stale class issues
```

### Deployment (Streamlit Cloud)
- Free tier hibernates apps after ~7 days of no traffic
- Sleeping apps return HTTP 303 → `share.streamlit.io/-/auth/app` (NOT an auth error)
- Always test on experiment endpoint, not localhost
- Use `/~/+/` path for browser automation (bypasses cross-origin iframe wrapper)
- Environment secrets set in Streamlit Cloud dashboard, not `.env` files

---

## 🚨 Worktree Setup (Mandatory)

Same as backend-architect — see `backend-architect-overlay.md` for worktree commands.

```bash
REPO_SHORT=$(basename "$(git remote get-url origin)" | sed 's/\.git$//' \
  | sed 's/churn_copilot_hendrix/churn/;s/character-life-sim/clse/;s/statuspulse/sp/')
WT_PATH="/tmp/wt/${REPO_SHORT}-<TICKET_NUM>"
git fetch origin experiment
git worktree add "$WT_PATH" -b "fix/${REPO_SHORT}-<TICKET_NUM>" origin/experiment
cd "$WT_PATH"
```

Do NOT remove the worktree — code reviewer and QA reuse it.

---

## 🚨 Pre-Submission Scope Check & Linting

Same gate as backend-architect — see `backend-architect-overlay.md`.

```bash
# Scope check (include in ticket comment)
git diff origin/experiment..HEAD --stat

# Lint gate (changed files only, zero violations)
ruff check --fix .
git diff origin/experiment..HEAD --name-only | grep '\.py$' | xargs -r ruff check
```

---

## Common Streamlit Bugs & Fixes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| "Works locally, fails on Cloud" | Missing module in `_RELOAD_MODULES` | Add to reload chain in `app.py` |
| Click button → page disappears | Using `if st.button()` instead of `on_click` | Switch to callback pattern |
| Data lost on page refresh | Using only `st.session_state` | Add `st.query_params` persistence |
| Pydantic validation error after deploy | Stale class from module cache | Add to `_RELOAD_MODULES` + dict roundtrip |
| "Duplicate widget ID" error | Same `key=` used in conditional branches | Make keys unique per branch |
| Slow page load | Missing `@st.cache_resource` on DB calls | Add caching decorator |

---

## Scope Discipline

Fix the ticket. Nothing else. If you find a related Streamlit bug, note it in your comment for a separate ticket. Minimal diff = easier review = faster pipeline.
