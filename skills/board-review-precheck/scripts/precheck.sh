#!/usr/bin/env bash
# Board Review Pre-Check — Zero-LLM ticket scanner
# Runs every 1 min via cron. Checks GitHub for actionable tickets.
# When work is found, wakes the correct product CTO session on demand.
# Posts hourly Slack summaries when quiet.
#
# Usage: precheck.sh [--dry-run]
# Env:   PRECHECK_STATE        — path to state JSON
#        SLACK_CHANNEL         — Slack channel ID for summaries
#        WORKSPACE             — workspace root (default: ~/.openclaw/workspace)
#        SUMMARY_INTERVAL_MIN  — minutes between hourly summaries (default: 60)

set -euo pipefail

# --- gh auth: use file-based token if keyring unavailable (cron) ---
GH_TOKEN_FILE="${HOME}/.config/gh-cron-token"
if [[ -z "${GH_TOKEN:-}" ]] && [[ -f "$GH_TOKEN_FILE" ]]; then
  export GH_TOKEN=$(cat "$GH_TOKEN_FILE")
fi

# --- Config ---
DRY_RUN="${1:-}"
WORKSPACE="${WORKSPACE:-$HOME/.openclaw/workspace}"
STATE_FILE="${PRECHECK_STATE:-$WORKSPACE/framework/board-review/PRECHECK_STATE.json}"
CTO_PROMPT_FILE="$WORKSPACE/framework/board-review/CTO_PROMPT.md"
SLACK_CHANNEL="${SLACK_CHANNEL:-C0ABYMAUV3M}"
SUMMARY_INTERVAL="${SUMMARY_INTERVAL_MIN:-60}"
FAILURE_STATE_FILE="${PRECHECK_FAILURE_STATE:-$WORKSPACE/framework/board-review/PRECHECK_FAILURE_STATE.json}"
FAILURE_ALERT_INTERVAL_MIN="${FAILURE_ALERT_INTERVAL_MIN:-60}"
LOCK_DIR="$WORKSPACE/framework/board-review/runlocks"
mkdir -p "$LOCK_DIR"
mkdir -p "$(dirname "$STATE_FILE")"
mkdir -p "$(dirname "$FAILURE_STATE_FILE")"
RUN_ACTIVITY_WINDOW_SEC="${RUN_ACTIVITY_WINDOW_SEC:-300}"
QUEUE_REVIEW_COOLDOWN_MIN="${QUEUE_REVIEW_COOLDOWN_MIN:-60}"
# Repos to scan — single source of truth
REPOS_FILE="$WORKSPACE/framework/board-review/REPOS.conf"
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

# --- Helpers ---
now_utc() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

now_epoch() { date +%s; }

iso_to_epoch() {
  if TZ=UTC date -j -f "%Y-%m-%dT%H:%M:%SZ" "$1" +%s 2>/dev/null; then
    return
  fi
  date -d "$1" +%s 2>/dev/null || echo "0"
}

log() { echo "[precheck $(date +%H:%M:%S)] $*"; }

ensure_failure_state() {
  if [[ ! -f "$FAILURE_STATE_FILE" ]]; then
    printf '{"activeFailures":{}}\n' > "$FAILURE_STATE_FILE"
  fi
}

failure_minutes_since() {
  local iso="$1"
  [[ -n "$iso" && "$iso" != "null" ]] || {
    echo 999999
    return
  }

  local then_epoch now_ts
  then_epoch=$(iso_to_epoch "$iso")
  now_ts=$(now_epoch)
  echo $(( (now_ts - then_epoch) / 60 ))
}

send_failure_alert() {
  local key="$1"
  local summary="$2"
  local detail="$3"
  local msg="⚠️ Board Review Precheck Failure (auto)\n\nComponent: ${key}\nSummary: ${summary}"

  if [[ -n "$detail" ]]; then
    msg+="\nDetail: ${detail}"
  fi

  msg+="\n\nThis alert repeats at most once per ${FAILURE_ALERT_INTERVAL_MIN} minutes while the failure persists."

  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    log "[DRY RUN] Would send failure alert: $msg"
  else
    openclaw message send --channel slack --target "$SLACK_CHANNEL" --message "$msg" 2>&1 || log "Warning: failure alert send failed"
  fi
}

record_failure() {
  local key="$1"
  local summary="$2"
  local detail="${3:-}"
  local now_iso existing_alert mins_since should_alert

  ensure_failure_state
  now_iso=$(now_utc)
  existing_alert=$(jq -r --arg key "$key" '.activeFailures[$key].lastAlertAt // ""' "$FAILURE_STATE_FILE" 2>/dev/null || true)
  mins_since=$(failure_minutes_since "$existing_alert")
  should_alert=0
  if [[ -z "$existing_alert" || "$existing_alert" == "null" || $mins_since -ge $FAILURE_ALERT_INTERVAL_MIN ]]; then
    should_alert=1
  fi

  jq \
    --arg key "$key" \
    --arg now "$now_iso" \
    --arg summary "$summary" \
    --arg detail "$detail" \
    --argjson shouldAlert "$should_alert" \
    '.activeFailures = (.activeFailures // {})
     | .activeFailures[$key] = ((.activeFailures[$key] // {})
         + {lastSeenAt: $now, summary: $summary, detail: $detail}
         + (if $shouldAlert == 1 then {lastAlertAt: $now} else {} end))' \
    "$FAILURE_STATE_FILE" > "${FAILURE_STATE_FILE}.tmp" && mv "${FAILURE_STATE_FILE}.tmp" "$FAILURE_STATE_FILE"

  log "FAILURE[$key]: $summary${detail:+ — $detail}"
  if [[ "$should_alert" == "1" ]]; then
    send_failure_alert "$key" "$summary" "$detail"
  fi
}

clear_failure() {
  local key="$1"
  [[ -f "$FAILURE_STATE_FILE" ]] || return 0
  jq --arg key "$key" 'if (.activeFailures // {} | has($key)) then .activeFailures |= del(.[$key]) else . end' \
    "$FAILURE_STATE_FILE" > "${FAILURE_STATE_FILE}.tmp" && mv "${FAILURE_STATE_FILE}.tmp" "$FAILURE_STATE_FILE"
}

unexpected_error_trap() {
  local rc="$1"
  local line="$2"
  local cmd="$3"
  record_failure "precheck-runtime" "precheck.sh exited unexpectedly" "line ${line}: ${cmd} (exit ${rc})"
  exit "$rc"
}

trap 'unexpected_error_trap "$?" "$LINENO" "$BASH_COMMAND"' ERR

# Rate-limit circuit breaker
# Reads OpenClaw's own cron job state — no model hardcoding, no provider API calls.
# If the most recent Board Review CTO job failed with a rate-limit error within the
# last COOLDOWN_MIN minutes, block spawning to prevent the cascade.
COOLDOWN_MIN=15

is_rate_limited() {
  local now_ms last_run_ms last_error age_ms age_min
  now_ms=$(date +%s)000

  # Find the most recently completed (errored or ok) Board Review CTO job
  last_run_ms=$(openclaw cron list --json 2>/dev/null \
    | jq -r '[.jobs[] | select(.name | test("Board Review CTO")) | select(.state.lastRunAtMs != null)] | sort_by(.state.lastRunAtMs) | last | .state.lastRunAtMs // "0"' 2>/dev/null)
  last_error=$(openclaw cron list --json 2>/dev/null \
    | jq -r '[.jobs[] | select(.name | test("Board Review CTO")) | select(.state.lastRunAtMs != null)] | sort_by(.state.lastRunAtMs) | last | .state.lastError // ""' 2>/dev/null)

  [[ -z "$last_run_ms" || "$last_run_ms" == "0" || "$last_run_ms" == "null" ]] && return 1

  # Check if error is rate-limit related (OpenClaw uses "rate_limit" and "cooldown" in error text)
  if ! echo "$last_error" | grep -qiE "rate_limit|cooldown"; then
    return 1
  fi

  # Check if error was within cooldown window
  age_ms=$(( now_ms - last_run_ms ))
  age_min=$(( age_ms / 60000 ))

  if [[ $age_min -lt $COOLDOWN_MIN ]]; then
    log "Rate-limit guard: last CTO job failed with rate limit ${age_min}m ago (cooldown=${COOLDOWN_MIN}m). Skipping spawn."
    return 0  # is rate limited
  fi

  return 1  # cooldown window passed, safe to spawn
}

# Check if a CTO board review session is already running
# Ignores sessions running longer than 45 min (treat as stale/stuck)
CTO_STALE_MIN=45
is_cto_running() {
  local now_ms running
  now_ms=$(date +%s)000
  running=$(openclaw cron list --json 2>/dev/null \
    | jq -r --arg now "$now_ms" --arg stale "$((CTO_STALE_MIN * 60 * 1000))" \
      '.jobs[] | select(.name | test("Board Review CTO")) | select(.state.runningAtMs != null) | select(($now | tonumber) - .state.runningAtMs < ($stale | tonumber)) | .id' 2>/dev/null)
  if [[ -n "$running" ]]; then
    echo "$running"
    return 0
  fi
  return 1
}

repo_to_product() {
  case "$1" in
    hendrixAIDev/churn_copilot_hendrix) echo "churnpilot" ;;
    hendrixAIDev/statuspulse) echo "statuspulse" ;;
    hendrixAIDev/hendrixAIDev) echo "framework" ;;
    hendrixAIDev/hendrixaidev.github.io) echo "personal-brand" ;;
    zrjaa1/openclaw-assistant) echo "openclaw-assistant" ;;
    hendrixAIDev/character-life-sim) echo "clse" ;;
    *) echo "" ;;
  esac
}

product_session_key() {
  case "$1" in
    churnpilot) echo "agent:main:cto-churnpilot" ;;
    statuspulse) echo "agent:main:cto-statuspulse" ;;
    framework) echo "agent:main:cto-framework" ;;
    personal-brand) echo "agent:main:cto-personal-brand" ;;
    openclaw-assistant) echo "agent:main:cto-openclaw-assistant" ;;
    clse) echo "agent:main:cto-clse" ;;
    *) echo "" ;;
  esac
}

product_session_id() {
  case "$1" in
    churnpilot) echo "46dfba9a-c319-41b9-b226-393a7ea10d1a" ;;
    statuspulse) echo "1b90c3d8-1497-40ad-be99-3a75d46a8635" ;;
    framework) echo "c164faba-3307-4cb9-9a7a-38bebf3f5b81" ;;
    personal-brand) echo "77713b76-a090-49ae-abf4-1240e9980787" ;;
    openclaw-assistant) echo "b367f243-2b76-4eaf-8e1a-4799ddc4f776" ;;
    clse) echo "a1c3afc0-fdcf-4271-9a15-ae0f7bedcca2" ;;
    *) echo "" ;;
  esac
}

product_label() {
  case "$1" in
    churnpilot) echo "ChurnPilot" ;;
    statuspulse) echo "StatusPulse" ;;
    framework) echo "Framework" ;;
    personal-brand) echo "Personal Brand" ;;
    openclaw-assistant) echo "OpenClaw Assistant" ;;
    clse) echo "CLSE" ;;
    *) echo "$1" ;;
  esac
}

product_lock_file() {
  echo "$LOCK_DIR/cto-$1.lock"
}

product_task_queue_path() {
  case "$1" in
    churnpilot) echo "$WORKSPACE/projects/churn_copilot/plans/task-queue.yaml" ;;
    framework) echo "$WORKSPACE/framework/plans/task_queue/tasks.yaml" ;;
    *) echo "" ;;
  esac
}

file_mtime_epoch() {
  local path="$1"
  [[ -e "$path" ]] || { echo "0"; return; }
  stat -f "%m" "$path" 2>/dev/null || echo "0"
}

file_sha256() {
  local path="$1"
  [[ -f "$path" ]] || { echo ""; return; }
  shasum -a 256 "$path" | awk '{print $1}'
}

lock_has_completion_marker() {
  local lock_file="$1"
  local log_file
  log_file=$(jq -r '.logFile // empty' "$lock_file" 2>/dev/null || true)
  [[ -n "$log_file" && -f "$log_file" ]] || return 1

  grep -q '"stopReason":"stop"' "$log_file" 2>/dev/null || \
    grep -q '"finalAssistantVisibleText"' "$log_file" 2>/dev/null
}

lock_last_activity_epoch() {
  local lock_file="$1"
  local session_id log_file session_file latest log_mtime session_mtime
  session_id=$(jq -r '.sessionId // empty' "$lock_file" 2>/dev/null || true)
  log_file=$(jq -r '.logFile // empty' "$lock_file" 2>/dev/null || true)
  session_file=""
  [[ -n "$session_id" ]] && session_file="$HOME/.openclaw/agents/main/sessions/${session_id}.jsonl"

  log_mtime=$(file_mtime_epoch "$log_file")
  session_mtime=$(file_mtime_epoch "$session_file")
  latest="$log_mtime"
  if [[ "$session_mtime" -gt "$latest" ]]; then
    latest="$session_mtime"
  fi
  echo "$latest"
}

is_product_cto_running() {
  local product="$1"
  local lock_file now_epoch started_epoch age_min pid activity_epoch idle_sec
  lock_file=$(product_lock_file "$product")
  [[ ! -f "$lock_file" ]] && return 1

  pid=$(jq -r '.pid // empty' "$lock_file" 2>/dev/null || true)
  started_epoch=$(jq -r '.startedEpoch // 0' "$lock_file" 2>/dev/null || echo "0")
  now_epoch=$(date +%s)
  age_min=$(( (now_epoch - started_epoch) / 60 ))

  if lock_has_completion_marker "$lock_file"; then
    log "Clearing ${product} CTO lock after completion marker was observed."
    rm -f "$lock_file"
    return 1
  fi

  activity_epoch=$(lock_last_activity_epoch "$lock_file")
  idle_sec=$(( now_epoch - activity_epoch ))

  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    if [[ "$activity_epoch" != "0" && "$idle_sec" -gt "$RUN_ACTIVITY_WINDOW_SEC" ]]; then
      log "Clearing stale ${product} CTO lock: pid=$pid idle=${idle_sec}s (> ${RUN_ACTIVITY_WINDOW_SEC}s)."
      rm -f "$lock_file"
      return 1
    fi
    echo "pid=$pid age=${age_min}m"
    return 0
  fi

  rm -f "$lock_file"
  return 1
}

# Wake the mapped product CTO session directly via its persistent session id.
# Intentionally silent: routine board-review wakes should not post to Slack unless the CTO
# explicitly decides there is something user-worthy to report.
trigger_cto() {
  local product="$1"
  local session_id="$2"
  local lock_file prompt pid log_file

  if [[ ! -f "$CTO_PROMPT_FILE" ]]; then
    log "ERROR: CTO prompt file not found: $CTO_PROMPT_FILE"
    return 1
  fi

  if [[ -z "$session_id" ]]; then
    log "ERROR: Missing session id for product $product"
    return 1
  fi

  lock_file=$(product_lock_file "$product")
  prompt=$(cat "$CTO_PROMPT_FILE")
  log_file="$WORKSPACE/framework/board-review/logs/cto-${product}-$(date +%Y%m%d-%H%M%S).log"
  mkdir -p "$WORKSPACE/framework/board-review/logs"

  echo "{\"startedAt\":\"$(now_utc)\",\"startedEpoch\":$(date +%s),\"sessionId\":\"$session_id\",\"product\":\"$product\",\"logFile\":\"$log_file\"}" > "$lock_file"

  (
    openclaw agent \
      --session-id "$session_id" \
      --message "$prompt" \
      --timeout 900 \
      --json > "$log_file" 2>&1
    rc=$?
    if [[ -f "$lock_file" ]]; then
      jq --arg endedAt "$(now_utc)" --argjson exitCode "$rc" '.endedAt = $endedAt | .exitCode = $exitCode' "$lock_file" > "${lock_file}.tmp" 2>/dev/null || true
      mv "${lock_file}.tmp" "$lock_file" 2>/dev/null || true
      rm -f "$lock_file"
    fi
    exit $rc
  ) &
  pid=$!

  jq --argjson pid "$pid" '.pid = $pid' "$lock_file" > "${lock_file}.tmp" && mv "${lock_file}.tmp" "$lock_file"
  echo "$pid"
}

# --- Step 1: Read state ---
LAST_CHECK="1970-01-01T00:00:00Z"
LAST_SUMMARY="1970-01-01T00:00:00Z"
CONSECUTIVE_SKIPS=0

if [[ ! -f "$STATE_FILE" ]]; then
  printf '{"lastCheckTime":"%s","lastSummaryTime":"%s","consecutiveSkips":0,"queueDigests":{}}\n' "$LAST_CHECK" "$LAST_SUMMARY" > "$STATE_FILE"
fi

ensure_failure_state

if [[ -f "$STATE_FILE" ]]; then
  LAST_CHECK=$(jq -r '.lastCheckTime // "1970-01-01T00:00:00Z"' "$STATE_FILE")
  LAST_SUMMARY=$(jq -r '.lastSummaryTime // "1970-01-01T00:00:00Z"' "$STATE_FILE")
  CONSECUTIVE_SKIPS=$(jq -r '.consecutiveSkips // 0' "$STATE_FILE")
fi

# --- Step 2: Verify gh auth works ---
# Note: gh auth status exits non-zero if keyring entry is stale, even when GH_TOKEN works.
# Test with an actual API call instead.
GH_OK=1
if ! gh api user --jq '.login' >/dev/null 2>&1; then
  GH_OK=0
  log "WARNING: gh API call failed — token may be expired or keyring inaccessible from cron"
  log "GitHub label scan will be skipped, but queue-based wake detection will still run"
  record_failure "github-auth" "GitHub auth unavailable for precheck" "gh api user failed; label scans are skipped until auth recovers"
else
  clear_failure "github-auth"
fi

# --- Step 3: Check for actionable tickets (label-based) ---
ACTIONABLE_ISSUES=()
TOTAL_OPEN=0

TRIGGER_LABELS=("status:new" "status:review" "status:verification" "status:cto-review")

if [[ "$GH_OK" == "1" ]]; then
  for repo in "${REPOS[@]}"; do
    repo_short="${repo##*/}"

    gh_err=""
    count=$(gh issue list --repo "$repo" --state open --json number --jq 'length' 2>/tmp/gh_err.txt) || {
      gh_err=$(cat /tmp/gh_err.txt)
      log "ERROR: gh issue list failed for $repo: $gh_err"
      record_failure "github-scan-$repo_short" "GitHub issue count scan failed for $repo" "$gh_err"
      count=0
    }
    if [[ -z "$gh_err" ]]; then
      clear_failure "github-scan-$repo_short"
    fi
    TOTAL_OPEN=$((TOTAL_OPEN + count))

    for label in "${TRIGGER_LABELS[@]}"; do
      label_scan_err=""
      found=$(gh issue list --repo "$repo" --state open --label "$label" \
        --json number,title,labels \
        --jq '.[] | "\(.number)|\(.title)|\([.labels[].name] | join(","))"' --limit 50 2>/tmp/gh_label_err.txt) || {
          label_scan_err=$(cat /tmp/gh_label_err.txt)
          log "ERROR: gh label scan failed for $repo [$label]: $label_scan_err"
          record_failure "github-label-$repo_short-$label" "GitHub label scan failed for $repo [$label]" "$label_scan_err"
          found=""
        }
      if [[ -z "$label_scan_err" ]]; then
        clear_failure "github-label-$repo_short-$label"
      fi

      if [[ -n "$found" ]]; then
        while IFS= read -r issue; do
          num="${issue%%|*}"
          rest="${issue#*|}"
          title="${rest%%|*}"
          labels="${rest#*|}"
          ACTIONABLE_ISSUES+=("$repo_short#$num [$label]: $title (labels: $labels)")
        done <<< "$found"
      fi
    done
  done
else
  log "Skipping GitHub actionable-ticket scan because GitHub auth is unavailable."
fi

# Deduplicate by issue number
SEEN_KEYS=""
UNIQUE_ISSUES=()
for issue in "${ACTIONABLE_ISSUES[@]+"${ACTIONABLE_ISSUES[@]}"}"; do
  key="${issue%% \[*}"
  if ! echo "$SEEN_KEYS" | grep -qF "|$key|"; then
    SEEN_KEYS="${SEEN_KEYS}|$key|"
    UNIQUE_ISSUES+=("$issue")
  fi
done

PRODUCTS_TO_WAKE=()
PRODUCT_WAKE_TEXT=""
PRODUCTS_SEEN="|"
for issue in "${UNIQUE_ISSUES[@]+"${UNIQUE_ISSUES[@]}"}"; do
  issue_key="${issue%% \[*}"
  repo_short="${issue_key%%#*}"
  case "$repo_short" in
    churn_copilot_hendrix) repo_full="hendrixAIDev/churn_copilot_hendrix" ;;
    statuspulse) repo_full="hendrixAIDev/statuspulse" ;;
    hendrixaidev.github.io) repo_full="hendrixAIDev/hendrixaidev.github.io" ;;
    hendrixAIDev) repo_full="hendrixAIDev/hendrixAIDev" ;;
    openclaw-assistant) repo_full="zrjaa1/openclaw-assistant" ;;
    character-life-sim) repo_full="hendrixAIDev/character-life-sim" ;;
    *) repo_full="" ;;
  esac

  product="$(repo_to_product "$repo_full")"
  [[ -z "$product" ]] && continue

  if [[ "$PRODUCTS_SEEN" != *"|$product|"* ]]; then
    PRODUCTS_SEEN="${PRODUCTS_SEEN}${product}|"
    PRODUCTS_TO_WAKE+=("$product")
  fi

  PRODUCT_WAKE_TEXT+="${product}|- ticket trigger: ${issue}"$'\n'
done

QUEUE_CHANGED_PRODUCTS=()
QUEUE_BACKLOG_PRODUCTS=()
QUEUE_DIGESTS_JSON='{}'
for product in churnpilot framework; do
  queue_path="$(product_task_queue_path "$product")"
  [[ -n "$queue_path" && -f "$queue_path" ]] || continue

  digest="$(file_sha256 "$queue_path")"
  [[ -n "$digest" ]] || continue

  prev_digest=""
  if [[ -f "$STATE_FILE" ]]; then
    prev_digest=$(jq -r --arg product "$product" '.queueDigests[$product] // ""' "$STATE_FILE" 2>/dev/null || true)
  fi

  QUEUE_DIGESTS_JSON=$(jq --arg product "$product" --arg digest "$digest" '. + {($product): $digest}' <<< "$QUEUE_DIGESTS_JSON")

  if [[ -z "$prev_digest" || "$prev_digest" != "$digest" ]]; then
    if [[ "$PRODUCTS_SEEN" != *"|$product|"* ]]; then
      PRODUCTS_SEEN="${PRODUCTS_SEEN}${product}|"
      PRODUCTS_TO_WAKE+=("$product")
    fi
    QUEUE_CHANGED_PRODUCTS+=("$product")
    if [[ -z "$prev_digest" ]]; then
      PRODUCT_WAKE_TEXT+="${product}|- queue trigger: initial snapshot of $(basename "$queue_path")"$'\n'
    else
      PRODUCT_WAKE_TEXT+="${product}|- queue trigger: $(basename "$queue_path") changed"$'\n'
    fi
  fi

  backlog_json=$(ruby -rjson -rpsych -rtime -e '
    path = ARGV[0]
    cooldown_min = ARGV[1].to_i
    now = Time.now
    tasks = (Psych.load_file(path)["tasks"] || [])
    eligible = tasks.select do |task|
      status = task["status"].to_s
      github_issue = task["github_issue"].to_s.strip
      ["proposed", "triaged"].include?(status) && github_issue.empty?
    end
    due = eligible.select do |task|
      reviewed_at = task["last_cto_reviewed_at"].to_s.strip
      next true if reviewed_at.empty?
      begin
        ((now - Time.parse(reviewed_at)) / 60.0) >= cooldown_min
      rescue
        true
      end
    end
    summary = {
      eligible_count: eligible.length,
      due_count: due.length,
      due_items: due.map do |task|
        {
          id: task["id"],
          status: task["status"],
          title: task["title"],
          last_cto_reviewed_at: task["last_cto_reviewed_at"]
        }
      end
    }
    puts JSON.generate(summary)
  ' "$queue_path" "$QUEUE_REVIEW_COOLDOWN_MIN" 2>/tmp/precheck_queue_err.txt) || {
    queue_err=$(cat /tmp/precheck_queue_err.txt)
    product_name=$(product_label "$product")
    record_failure "queue-parse-$product" "Task queue parse failed for ${product_name}" "$queue_err"
    log "ERROR: task queue parse failed for ${product_name}: $queue_err"
    continue
  }
  clear_failure "queue-parse-$product"

  eligible_count=$(jq -r '.eligible_count // 0' <<< "$backlog_json")
  due_count=$(jq -r '.due_count // 0' <<< "$backlog_json")

  if [[ "$due_count" -gt 0 ]]; then
    repo_full=""
    case "$product" in
      churnpilot) repo_full="hendrixAIDev/churn_copilot_hendrix" ;;
      framework) repo_full="hendrixAIDev/hendrixAIDev" ;;
    esac

    active_count=0
    if [[ "$GH_OK" == "1" && -n "$repo_full" ]]; then
      active_count=$(gh issue list --repo "$repo_full" --state open --json number,labels \
        --jq '[.[] | select(([.labels[].name] | any(. == "status:new" or . == "status:in-progress" or . == "status:review" or . == "status:verification" or . == "status:cto-review")))] | length' \
        2>/dev/null || echo "0")
    fi

    if [[ "$active_count" -eq 0 ]]; then
      if [[ "$PRODUCTS_SEEN" != *"|$product|"* ]]; then
        PRODUCTS_SEEN="${PRODUCTS_SEEN}${product}|"
        PRODUCTS_TO_WAKE+=("$product")
      fi
      QUEUE_BACKLOG_PRODUCTS+=("$product")

      while IFS= read -r backlog_line; do
        [[ -n "$backlog_line" ]] || continue
        PRODUCT_WAKE_TEXT+="${product}|- queue backlog due: ${backlog_line}"$'\n'
      done < <(jq -r '.due_items[] | "\(.id) [\(.status)]: \(.title) (last_cto_reviewed_at: \(.last_cto_reviewed_at // "never"))"' <<< "$backlog_json")
    fi
  fi
done

log "Found ${#UNIQUE_ISSUES[@]} actionable tickets, ${#QUEUE_CHANGED_PRODUCTS[@]} queue-change trigger(s), and ${#QUEUE_BACKLOG_PRODUCTS[@]} due queue-backlog trigger(s) across ${#PRODUCTS_TO_WAKE[@]} product CTO session(s), $TOTAL_OPEN total open"

# --- Step 4: Decision ---
NOW=$(now_utc)
NOW_EPOCH=$(now_epoch)
LAST_SUMMARY_EPOCH=$(iso_to_epoch "$LAST_SUMMARY")
MINUTES_SINCE_SUMMARY=$(( (NOW_EPOCH - LAST_SUMMARY_EPOCH) / 60 ))

if [[ ${#UNIQUE_ISSUES[@]} -gt 0 || ${#QUEUE_CHANGED_PRODUCTS[@]} -gt 0 || ${#QUEUE_BACKLOG_PRODUCTS[@]} -gt 0 ]]; then
  if is_rate_limited; then
    jq --arg now "$NOW" --argjson queueDigests "$QUEUE_DIGESTS_JSON" \
      '.lastCycleUtc = $now | .queueDigests = ((.queueDigests // {}) + $queueDigests)' \
      "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
  else
    SPAWNED_ANY=0
    for product in "${PRODUCTS_TO_WAKE[@]+"${PRODUCTS_TO_WAKE[@]}"}"; do
      session_key="$(product_session_key "$product")"
      session_id="$(product_session_id "$product")"
      product_name="$(product_label "$product")"
      [[ -z "$session_key" || -z "$session_id" ]] && continue

      wake_reasons=$(printf "%s" "$PRODUCT_WAKE_TEXT" | awk -F'|' -v p="$product" '$1==p {print $2}')

      if RUNNING_NAME=$(is_product_cto_running "$product"); then
        log "${product_name} CTO already running ($RUNNING_NAME). Skipping wake."
        [[ -n "$wake_reasons" ]] && log "Wake reasons for ${product_name}:"$'\n'"$wake_reasons"
        continue
      fi

      log "Waking ${product_name} CTO session (${session_key}, ${session_id})"
      [[ -n "$wake_reasons" ]] && log "Wake reasons for ${product_name}:"$'\n'"$wake_reasons"

      if [[ "$DRY_RUN" == "--dry-run" ]]; then
        log "[DRY RUN] Would wake ${product_name} via session id ${session_id}"
      else
        trigger_cto "$product" "$session_id" >/dev/null || log "Warning: ${product_name} CTO wake returned non-zero"
      fi
      SPAWNED_ANY=1
    done

    jq --arg now "$NOW" --arg skips "0" --argjson queueDigests "$QUEUE_DIGESTS_JSON" \
      '.lastCheckTime = $now | .lastCycleUtc = $now | .consecutiveSkips = ($skips | tonumber) | .queueDigests = ((.queueDigests // {}) + $queueDigests)' \
      "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

    if [[ "$SPAWNED_ANY" == "1" ]]; then
      log "State updated. Product CTO wakes queued."
    else
      log "State updated. No new CTO wakes were needed."
    fi
  fi

elif [[ $MINUTES_SINCE_SUMMARY -ge $SUMMARY_INTERVAL ]]; then
  log "Hourly summary due ($MINUTES_SINCE_SUMMARY min since last)"

  REPO_COUNTS=""
  if [[ "$GH_OK" == "1" ]]; then
    for repo in "${REPOS[@]}"; do
      repo_short="${repo##*/}"
      count=$(gh issue list --repo "$repo" --state open --json number --jq 'length' 2>/dev/null || echo "0")
      case "$repo_short" in
        churn_copilot_hendrix) REPO_COUNTS="$REPO_COUNTS[$count] ChurnPilot | " ;;
        statuspulse)           REPO_COUNTS="$REPO_COUNTS[$count] StatusPulse | " ;;
        hendrixAIDev)          REPO_COUNTS="$REPO_COUNTS[$count] Framework | " ;;
        character-life-sim)    REPO_COUNTS="$REPO_COUNTS[$count] CLSE | " ;;
        openclaw-assistant)    REPO_COUNTS="$REPO_COUNTS[$count] OCA" ;;
      esac
    done
  else
    REPO_COUNTS="GitHub auth unavailable"
  fi

  SUMMARY_MSG="🗳️ Board Review — Hourly Status (auto)

All quiet. No actionable tickets.
Open issues: ${REPO_COUNTS}
Next check: 1 min"

  if [[ "$DRY_RUN" == "--dry-run" ]]; then
    log "[DRY RUN] Would send summary: $SUMMARY_MSG"
  else
    openclaw message send --channel slack --target "$SLACK_CHANNEL" --message "$SUMMARY_MSG" 2>&1 || log "Warning: message send failed"
  fi

  NEW_SKIPS=$((CONSECUTIVE_SKIPS + 1))
  jq --arg now "$NOW" --arg skips "$NEW_SKIPS" --argjson queueDigests "$QUEUE_DIGESTS_JSON" \
    '.lastCheckTime = $now | .lastSummaryTime = $now | .lastCycleUtc = $now | .consecutiveSkips = ($skips | tonumber) | .queueDigests = ((.queueDigests // {}) + $queueDigests)' \
    "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

  log "Hourly summary posted."

else
  NEW_SKIPS=$((CONSECUTIVE_SKIPS + 1))
  jq --arg now "$NOW" --arg skips "$NEW_SKIPS" --argjson queueDigests "$QUEUE_DIGESTS_JSON" \
    '.lastCheckTime = $now | .lastCycleUtc = $now | .consecutiveSkips = ($skips | tonumber) | .queueDigests = ((.queueDigests // {}) + $queueDigests)' \
    "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

  log "No updates. $MINUTES_SINCE_SUMMARY min since last summary (next at ${SUMMARY_INTERVAL}m). Silent."
fi

clear_failure "precheck-runtime"
