#!/usr/bin/env bash
# Board Review Watchdog — Zero-LLM stale ticket detector
# Checks all WIP tickets across repos. If last comment is >STALE_MIN old,
# resets to status:new for re-dispatch.
#
# Usage: watchdog.sh [--dry-run]
# Env:   STALE_MIN    — staleness threshold in minutes (default: 45)
#        WORKSPACE    — workspace root (default: ~/.openclaw/workspace)

set -euo pipefail

# --- gh auth: use file-based token if keyring unavailable (cron) ---
GH_TOKEN_FILE="${HOME}/.config/gh-cron-token"
if [[ -z "${GH_TOKEN:-}" ]] && [[ -f "$GH_TOKEN_FILE" ]]; then
  export GH_TOKEN=$(cat "$GH_TOKEN_FILE")
fi

# --- Config ---
DRY_RUN="${1:-}"
WORKSPACE="${WORKSPACE:-$HOME/.openclaw/workspace}"
REPOS_FILE="$WORKSPACE/framework/board-review/REPOS.conf"
STALE_MIN="${STALE_MIN:-45}"

# Only check status:in-progress — that's the "sub-agent working" state.
# Other statuses (review, verification, cto-review) mean "ready for CTO"
# and should NOT be reset by the watchdog.
WIP_LABELS=("status:in-progress")

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# --- Load repos ---
REPOS=()
if [[ -f "$REPOS_FILE" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    REPOS+=("$line")
  done < "$REPOS_FILE"
else
  log "ERROR: Repos config not found: $REPOS_FILE"
  exit 1
fi

# --- Verify gh auth ---
if ! gh api user --jq '.login' &>/dev/null; then
  log "ERROR: gh auth failed"
  exit 1
fi

# --- Timestamp math ---
now_epoch() { date +%s; }

iso_to_epoch() {
  # Convert ISO-8601 UTC timestamp to epoch seconds (reliable cross-platform)
  python3 -c "
from datetime import datetime
ts = '$1'.replace('Z', '+00:00')
print(int(datetime.fromisoformat(ts).timestamp()))
" 2>/dev/null || echo 0
}

# --- Main ---
NOW=$(now_epoch)
RESET_COUNT=0

for REPO in "${REPOS[@]}"; do
  for LABEL in "${WIP_LABELS[@]}"; do
    # Get issues with this WIP label
    ISSUES=$(gh issue list --repo "$REPO" --label "$LABEL" --state open --json number,title --jq '.[].number' 2>/dev/null || true)

    [[ -z "$ISSUES" ]] && continue

    for ISSUE_NUM in $ISSUES; do
      # Get last comment timestamp
      LAST_COMMENT_TS=$(gh issue view "$ISSUE_NUM" --repo "$REPO" --json comments \
        --jq 'if (.comments | length) > 0 then .comments[-1].createdAt else "" end' 2>/dev/null || true)

      if [[ -z "$LAST_COMMENT_TS" ]]; then
        # No comments — use issue creation date as fallback
        LAST_COMMENT_TS=$(gh issue view "$ISSUE_NUM" --repo "$REPO" --json createdAt --jq '.createdAt' 2>/dev/null || true)
      fi

      [[ -z "$LAST_COMMENT_TS" ]] && continue

      COMMENT_EPOCH=$(iso_to_epoch "$LAST_COMMENT_TS")
      DIFF_MIN=$(( (NOW - COMMENT_EPOCH) / 60 ))

      if [[ $DIFF_MIN -gt $STALE_MIN ]]; then
        log "STALE: $REPO#$ISSUE_NUM ($LABEL) — last activity ${DIFF_MIN}m ago (threshold: ${STALE_MIN}m)"

        if [[ "$DRY_RUN" == "--dry-run" ]]; then
          log "  [DRY RUN] Would reset to status:new"
        else
          # Reset to status:new
          gh issue edit "$ISSUE_NUM" --repo "$REPO" \
            --remove-label "$LABEL" --add-label "status:new" 2>/dev/null

          gh issue comment "$ISSUE_NUM" --repo "$REPO" \
            --body "### Watchdog Reset — $(date '+%Y-%m-%d %H:%M %Z')

**Reason:** Stuck in \`$LABEL\` for ${DIFF_MIN} minutes with no comment activity (threshold: ${STALE_MIN}m). Sub-agent likely died or was never spawned.

Resetting to \`status:new\` for fresh triage and re-dispatch." 2>/dev/null

          log "  Reset $REPO#$ISSUE_NUM to status:new"
          RESET_COUNT=$((RESET_COUNT + 1))
        fi
      else
        log "OK: $REPO#$ISSUE_NUM ($LABEL) — last activity ${DIFF_MIN}m ago"
      fi
    done
  done
done

log "Done. Reset $RESET_COUNT stale ticket(s)."
