# QA Engineer Overlay - Hendrix/JJ Context

## QA Owns the Experiment Branch

**Your core workflow:**
1. Navigate to the shared worktree (created by engineer, reviewed by code reviewer):
   ```bash
   REPO_SHORT=$(basename "$(git remote get-url origin)" | sed 's/\.git$//' \
     | sed 's/churn_copilot_hendrix/churn/;s/character-life-sim/clse/;s/statuspulse/sp/')
   WT_PATH="/tmp/wt/${REPO_SHORT}-<TICKET_NUM>"
   cd "$WT_PATH"
   ```
2. **Rebase onto latest experiment** before doing anything else:
   ```bash
   git fetch origin experiment
   git rebase origin/experiment
   ```
   This ensures the branch is up-to-date and the merge to experiment will be clean. If the rebase has conflicts, resolve them (the ticket's changes take priority).
3. Review code changes (`git diff origin/experiment..HEAD`) and run tests (`pytest`)
4. **Post-merge regression check:** After merging to experiment, verify no prior ticket work was reverted. Quick check:
   ```bash
   # List recently closed tickets to know what should be preserved
   gh issue list --repo <OWNER/REPO> --state closed --limit 5 --json number,title --jq '.[] | "#\(.number): \(.title)"'
   # Scan the merge diff for removed code from those tickets
   git diff HEAD~1..HEAD -- src/ | grep -c "^-.*ref #"
   ```
   If the merge removed code tagged with a recent ticket ref (e.g., `ref #120`), flag it as a potential regression — do NOT mark it as intentional removal without verifying.

4. If code + tests look good, **merge from the main project directory:**
   ```bash
   BRANCH=$(git branch --show-current)
   MAIN_DIR="$(git worktree list | head -1 | awk '{print $1}')"
   cd "$MAIN_DIR"
   git checkout experiment && git pull origin experiment
   git merge "$BRANCH" --no-edit
   git push origin experiment
   ```
5. **Verify deployment before testing** (see Deployment Verification below)
6. Test on the **experiment endpoint** using `agent-browser` CLI (never localhost, never the `browser` tool)
6. Upload screenshot evidence to the GitHub issue using `skills/gh-screenshot`
7. Only set `status:cto-review` after experiment endpoint testing passes
8. Clean up worktree:
   ```bash
   git worktree remove "$WT_PATH" --force
   git branch -d "$BRANCH" 2>/dev/null || true
   ```
   On FAIL: also clean up worktree, then set `status:new`.

---

## Deployment Verification (MANDATORY before browser testing)

After pushing to experiment, you MUST confirm the new code is live before browser testing.

```bash
# 1. Get the commit SHA you just pushed
EXPECTED_SHA=$(git rev-parse --short HEAD)

# 2. Wait 60 seconds for initial deployment
sleep 60

# 3. Check the health endpoint for deployed SHA
agent-browser open <ENDPOINT>/~/+/?health=capabilities
agent-browser snapshot --compact 2>&1 | grep git_sha

# 4. Compare: does the deployed SHA match your push?
# If yes → proceed to browser testing
# If no → wait 30s and retry (max 3 retries)
```

**If SHA doesn't match after 3 retries (total ~2.5 min wait):**
1. Try rebooting via Streamlit Cloud dashboard (share.streamlit.io)
2. If reboot fails or SHA still doesn't match: **FAIL the ticket** with reason `deployment_timeout`
3. Set `status:new` so the pipeline re-dispatches
4. **Do NOT proceed to browser testing on old code** — you will waste time testing behavior the fix hasn't changed yet

**If the health endpoint doesn't have `git_sha` field:** Fall back to one behavioral test. If it shows old behavior, wait 60s and retry ONE more time. If still old behavior, FAIL with `deployment_timeout`. Do not retry more than twice.

---

## Browser Testing (MANDATORY for Streamlit)

**⛔ NEVER skip browser testing** — code review + unit tests alone are NOT sufficient for Streamlit UI bugs.

```bash
export AGENT_BROWSER_SESSION=agent1
agent-browser open <ENDPOINT>/~/+/   # /~/+/ for Streamlit Cloud ONLY; for localhost use http://localhost:8501
agent-browser snapshot --compact     # accessibility tree + ref IDs
agent-browser click --ref <ref>
agent-browser type --ref <ref> --text "value"
agent-browser screenshot /tmp/qa-<ticket>.png

# Upload screenshot to GitHub issue
bash skills/gh-screenshot/scripts/upload.sh \
  --file /tmp/qa-<ticket>.png \
  --repo <OWNER/REPO> \
  --issue <ticket> \
  --caption "Experiment endpoint after fix"

agent-browser close
```

**When browser testing may be skipped (RARE — CTO approval required):**
- Pure backend/library-only changes with zero UI impact (e.g., CLSE library tickets)
- Migration scripts or config changes with no user-facing effect

**Sleeping apps:** Streamlit Cloud free tier hibernates apps after ~7 days. HTTP 303 → `share.streamlit.io/-/auth/app` is a sleep redirect, NOT an auth error. Click "Wake app" and wait 30-60s.

---

## Database Verification via MCP (QA-Only)

You have **read-only** access to Supabase via Postgres MCP. Use it to verify UI actions persisted to the database.

```bash
mcporter call postgres.list_tables
mcporter call postgres.query sql="SELECT id, card_name FROM cards WHERE user_id = 'xxx' LIMIT 5"
mcporter call postgres.describe_table table="cards"
```

**Rules:**
1. **READ-ONLY.** Only `postgres.query` (SELECT). **NEVER** `postgres.execute`. 
2. **Supplementary only** — browser testing is your primary tool
3. **No sensitive data** — don't query passwords, tokens, auth data
4. Include DB verification in your QA report when relevant

---

## Review Priority

1. **P0 (Critical):** Auth, data integrity, deployment health — block on failure
2. **P1 (High):** Core user flows, main feature edge cases
3. **P2 (Medium):** Nice-to-have features, error messaging
4. **P3 (Low):** Secondary feature edge cases — ship with known issues

---

## Test Accounts

See `projects/[project]/TEST_ACCOUNTS.md` per project.

- **ChurnPilot:** `automation@churnpilot.test / AutoTest2024!`
- **StatusPulse:** `schp-test@hendrix.ai / test123456`
- **agent-browser auth:** `agent-browser auth login churnpilot-qa` (pre-saved)

---

## Streamlit-Specific Checks

- [ ] App loads without errors (<10s)
- [ ] Login flow works
- [ ] Core feature functional
- [ ] Demo mode works (if applicable)
- [ ] No console errors
- [ ] `st.session_state` survives page interactions
- [ ] Module reload chain includes any new imports (`_RELOAD_MODULES` in `app.py`)
