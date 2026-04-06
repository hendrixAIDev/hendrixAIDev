# Streamlit Gotchas — Compiled from EvoMap Capsules

**Source:** 15 production incidents (tickets #56, #60, #64, #65, #66, #67, #69, #70, #71, #77, #80, #83, #88, #92, SP-12)
**Last updated:** 2026-03-08
**Used by:** fullstack-engineer-overlay, frontend-engineer-overlay

---

## Execution Model

Streamlit re-runs the **entire script** on every interaction (button click, input change, `st.rerun()`). Local variables reset every run. State persists ONLY via `st.session_state`.

---

## 1. Session State Lifecycle

### Setting flags without rerun (ticket #64)
Setting `session_state` flags in a button callback without calling `st.rerun()` means the UI won't update — the flag is set but Streamlit doesn't re-render.
```python
# ❌ Flag set but UI unchanged
def on_click():
    st.session_state.show_modal = True

# ✅ Force rerun after state change
def on_click():
    st.session_state.show_modal = True
    st.rerun()
```

### Flag checked during list mutation (ticket #65)
Setting a session_state flag in a callback then checking it in a rendering loop fails when the item moves between lists after the callback. Toast fires on wrong action.
**Fix:** Validate the flag against current list state, not stale state.

### Callback scope — closures don't work (ticket #70)
Callbacks execute in a different rerun scope where outer local variables may not be available. Using a local `storage` variable in a callback causes `AttributeError`.
```python
# ❌ Closure variable lost in callback scope
def render():
    storage = get_storage()
    st.button("Save", on_click=lambda: storage.save())  # storage may be None

# ✅ Pass through session_state
def render():
    st.session_state._storage = get_storage()
    st.button("Save", on_click=save_handler)

def save_handler():
    st.session_state._storage.save()
```

### Defensive access (always)
```python
# ✅ Safe
value = st.session_state.get("key", default)

# ❌ Crashes on first run
value = st.session_state["key"]

# ✅ Initialize early
if "initialized" not in st.session_state:
    st.session_state.initialized = True
```

---

## 2. Button & Rerun Patterns

### if st.button() anti-pattern (ticket #67)
`if st.button()` causes the page to rerun top-to-bottom. If `editing_key` is evaluated BEFORE the button callback runs, the form renders again on the same pass.
```python
# ❌ "Click → page disappears → click again" bug
if st.button("Save"):
    save_data()  # Runs AFTER rerun starts

# ✅ on_click processes before rerun
st.button("Save", on_click=save_handler, args=(data,))
```

### Demo mode button unresponsive (ticket #92)
`show_user_menu()` was checking `session_token` and clearing `demo_mode` on rerun. The demo button appeared dead because the mode was being reset each cycle.
**Fix:** Guard demo_mode flag before auth checks.

---

## 3. Module Reload Chain (Top Bug Source)

### Missing module in _RELOAD_MODULES (tickets #66, #71, #78, #83, #88, #104)
Streamlit Cloud caches modules across reruns. Any new `src/core/` module must be in `_RELOAD_MODULES` in `app.py` or it causes `ModuleNotFoundError` or stale class issues on Cloud.

**Symptom:** "Works locally, fails on Cloud" or Pydantic validation errors after deploy.

```python
# In app.py — add ANY new core module here
_RELOAD_MODULES = [
    "src.core.auth",
    "src.core.database",
    "src.core.new_module",  # ← Don't forget this!
]
```

**Rule:** If you add or move ANY `src/core/` import, update `_RELOAD_MODULES`. This is a rejection reason at code review.

---

## 4. Tabs & Fragments

### st.tabs() — no server rerun on switch (ticket #56)
Tab switching is purely client-side CSS visibility toggle — no server rerun occurs. When `@st.fragment` updates data in one tab, sibling tabs keep their previously-rendered HTML.
**Fix:** Each tab must re-read from authoritative data source on render, not rely on cached state.

### st.fragment — doesn't react to external changes (ticket #71)
`@st.fragment` decorators don't re-run when `session_state` changes externally (from another tab/view). Fragments cache their own render state.
**Fix:** Each view must re-read from DB/authoritative source, not rely on fragment-level cache.

---

## 5. Thread Safety & Globals

### Module-level globals shared across users (ticket #80)
Module-level global lists (e.g., `_failed_operations`) are shared across ALL user sessions on the same worker. User A's failures can appear for User B.
**Fix:** Tag entries with `user_id`, or use `st.session_state` (per-session).

### Cache attributes shared between threads (ticket #77)
`DatabaseStorage` cache attributes (`_cards_cache`, `_cards_index`) shared between main Streamlit thread and background `ThreadPoolExecutor` threads without synchronization.
**Fix:** Add `threading.Lock()` for any shared mutable state.

---

## 6. CSS & Styling

### Aggressive CSS selectors hide sidebar toggle (ticket #69)
CSS rules hiding Streamlit chrome with selectors like `[data-testid='stHeader'] button {display: none !important}` also hide the sidebar collapse/expand toggle.
**Fix:** Use narrow, specific selectors. Test in both mobile and desktop views.

---

## 7. File & Project Structure

### Pages directory auto-detection (ticket #60)
Any `.py` file placed directly in a Streamlit `pages/` directory triggers automatic multi-page app detection, adding unwanted sidebar navigation links.
**Fix:** Prefix helper files with `_` (e.g., `_utils.py`) to prevent auto-detection.

---

## 8. Persistence

### Query params for page state (NOT cookies/localStorage)
```python
# ✅ Survives page refresh
st.query_params["page"] = "dashboard"

# ❌ Cookies — sandboxed iframe, can't write
# ❌ localStorage — iframe-scoped, won't persist across loads
# ❌ st.session_state alone — lost on page refresh
```

---

## 9. Caching

```python
# ✅ @st.cache_resource — DB connections, Pydantic models, non-serializable objects
# ✅ @st.cache_data — serializable data (DataFrames, dicts, lists)
# ❌ @st.cache_data with Pydantic models — fails silently or stale class issues
```

---

## 10. Deployment (Streamlit Cloud)

- Free tier hibernates apps after ~7 days of no traffic
- Sleeping apps return HTTP 303 → `share.streamlit.io/-/auth/app` (NOT an auth error)
- Use `/~/+/` path for Streamlit Cloud only (bypasses cross-origin iframe wrapper)
- For localhost, use bare URL — no `/~/+/` needed
- Environment secrets: set in Streamlit Cloud dashboard, not `.env` files
- `st.secrets` loads from `.streamlit/secrets.toml` but does NOT inject into `os.environ` (ticket SP-12)

---

## 11. Database (Supabase + Streamlit)

- **Connection string:** Always use pooler port 6543 (never 5432)
- **JOIN pitfalls:** Multiple LEFT JOINs across related tables produce Cartesian products before GROUP BY (ticket #66). Use pre-aggregated subqueries or CTEs.
- **Parameterized queries:** Always `cursor.execute("... WHERE id = %s", (id,))` — never f-strings
- **No direct DB writes in tests** — use app layer

---

*To add a new gotcha: create an EvoMap capsule first, then add the pattern here with ticket reference.*
