#!/usr/bin/env bash
# Offline contract tests for board-review precheck routing/state behavior.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PRECHECK_SCRIPT="$WORKSPACE_ROOT/skills/board-review-precheck/scripts/precheck.sh"
PASS_COUNT=0
FAIL_COUNT=0
TMP_ROOT=""
TMP_DIRS=()

cleanup() {
  local dir
  for dir in "${TMP_DIRS[@]:-}"; do
    [[ -n "$dir" && -d "$dir" ]] && rm -rf "$dir"
  done
}
trap cleanup EXIT

pass() { PASS_COUNT=$((PASS_COUNT + 1)); printf "ok - %s\n" "$1"; }
fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); printf "not ok - %s\n" "$1" >&2; }

assert_json() {
  local file="$1" filter="$2" name="$3"
  if jq -e "$filter" "$file" >/dev/null; then pass "$name"; else fail "$name"; jq "." "$file" >&2 || true; fi
}

assert_contains() {
  local file="$1" needle="$2" name="$3"
  if grep -Fq -- "$needle" "$file"; then pass "$name"; else fail "$name"; printf "missing %s in %s\n" "$needle" "$file" >&2; fi
}

setup_fixture() {
  TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/board-review-contract.XXXXXX")"
  TMP_DIRS+=("$TMP_ROOT")
  mkdir -p "$TMP_ROOT/bin" "$TMP_ROOT/workspace/framework/board-review/state" "$TMP_ROOT/workspace/framework/board-review/runlocks"
  mkdir -p "$TMP_ROOT/workspace/framework/plans/task_queue" "$TMP_ROOT/workspace/projects/churn_copilot/plans"
  cp "$WORKSPACE_ROOT/framework/board-review/CTO_PROMPT.md" "$TMP_ROOT/workspace/framework/board-review/CTO_PROMPT.md"
  cp "$WORKSPACE_ROOT/framework/board-review/REPOS.conf" "$TMP_ROOT/workspace/framework/board-review/REPOS.conf"
  cat > "$TMP_ROOT/workspace/framework/board-review/PRECHECK_STATE.json" <<JSON
{"lastCheckTime":"2026-05-15T00:00:00Z","lastSummaryTime":"2026-05-15T00:00:00Z","consecutiveSkips":0,"openIssues":[999],"queueDigests":{}}
JSON
  printf '{"activeFailures":{}}\n' > "$TMP_ROOT/workspace/framework/board-review/PRECHECK_FAILURE_STATE.json"
  printf '# ChurnPilot State\n' > "$TMP_ROOT/workspace/framework/board-review/state/churnpilot.md"
  printf '# Framework State\n' > "$TMP_ROOT/workspace/framework/board-review/state/framework.md"
  cat > "$TMP_ROOT/workspace/projects/churn_copilot/plans/task-queue.yaml" <<YAML
tasks:
  - id: cp-test-001
    status: done
    github_issue: hendrixAIDev/churn_copilot_hendrix#1
    title: Already handled
YAML
  cat > "$TMP_ROOT/workspace/framework/plans/task_queue/tasks.yaml" <<YAML
tasks:
  - id: fw-test-001
    status: done
    github_issue: hendrixAIDev/hendrixAIDev#1
    title: Already handled
YAML
  cat > "$TMP_ROOT/bin/openclaw" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
log_dir="${OPENCLAW_MOCK_LOG_DIR:?}"
mkdir -p "$log_dir"
if [[ "${1:-}" == "cron" && "${2:-}" == "list" ]]; then printf '{"jobs":[]}\n'; exit 0; fi
if [[ "${1:-}" == "agent" ]]; then
  session_id=""
  message=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --session-id) session_id="$2"; shift 2 ;;
      --message) message="$2"; shift 2 ;;
      --timeout) shift 2 ;;
      --json) shift ;;
      *) shift ;;
    esac
  done
  idx="$(find "$log_dir" -name "wake-*.txt" | wc -l | tr -d " ")"
  { printf "SESSION_ID=%s\n" "$session_id"; printf "%s\n" "---MESSAGE---"; printf "%s\n" "$message"; } > "$log_dir/wake-$idx.txt"
  printf '{"stopReason":"stop","finalAssistantVisibleText":"mock"}\n'
  exit 0
fi
if [[ "${1:-}" == "message" ]]; then exit 0; fi
printf "unexpected openclaw call: %s\n" "$*" >&2
exit 64
SH
  chmod +x "$TMP_ROOT/bin/openclaw"
}

write_gh_mock() {
  local scenario="$1"
  cat > "$TMP_ROOT/bin/gh" <<SH
#!/usr/bin/env bash
set -euo pipefail
scenario="$scenario"
if [[ "\${1:-}" == "api" && "\${2:-}" == "user" ]]; then printf "mock-user\n"; exit 0; fi
if [[ "\${1:-}" == "issue" && "\${2:-}" == "list" ]]; then
  repo=""; label=""; jq_expr=""
  while [[ \$# -gt 0 ]]; do
    case "\$1" in
      --repo) repo="\$2"; shift 2 ;;
      --label) label="\$2"; shift 2 ;;
      --jq) jq_expr="\$2"; shift 2 ;;
      --state|--json|--limit) shift 2 ;;
      *) shift ;;
    esac
  done
  if [[ "\$jq_expr" == "length" ]]; then
    case "\$scenario:\$repo" in
      labels:hendrixAIDev/churn_copilot_hendrix) printf "2\n" ;;
      prompts:hendrixAIDev/churn_copilot_hendrix|prompts:hendrixAIDev/hendrixAIDev) printf "1\n" ;;
      *) printf "0\n" ;;
    esac
    exit 0
  fi
  if [[ "\$jq_expr" == "[.[].number]" ]]; then
    case "\$scenario:\$repo" in
      labels:hendrixAIDev/churn_copilot_hendrix) printf "[101,202]\n" ;;
      prompts:hendrixAIDev/churn_copilot_hendrix) printf "[101]\n" ;;
      prompts:hendrixAIDev/hendrixAIDev) printf "[28]\n" ;;
      *) printf "[]\n" ;;
    esac
    exit 0
  fi
  if [[ "\$jq_expr" == *'any(. == "status:new"'* ]]; then printf "0\n"; exit 0; fi
  if [[ -n "\$label" ]]; then
    case "\$scenario:\$repo:\$label" in
      labels:hendrixAIDev/churn_copilot_hendrix:status:new) printf "101|Actionable from live label|status:new,priority:high\n" ;;
      prompts:hendrixAIDev/churn_copilot_hendrix:status:new) printf "101|ChurnPilot wake|status:new\n" ;;
      prompts:hendrixAIDev/hendrixAIDev:status:new) printf "28|Framework wake|status:new\n" ;;
    esac
    exit 0
  fi
  printf "[]\n"; exit 0
fi
printf "unexpected gh call: %s\n" "\$*" >&2
exit 64
SH
  chmod +x "$TMP_ROOT/bin/gh"
}

run_precheck() {
  local scenario="$1" mode="${2:---dry-run}"
  write_gh_mock "$scenario"
  if [[ "$mode" == "live" ]]; then
    PATH="$TMP_ROOT/bin:$PATH" WORKSPACE="$TMP_ROOT/workspace" PRECHECK_STATE="$TMP_ROOT/workspace/framework/board-review/PRECHECK_STATE.json" PRECHECK_FAILURE_STATE="$TMP_ROOT/workspace/framework/board-review/PRECHECK_FAILURE_STATE.json" OPENCLAW_MOCK_LOG_DIR="$TMP_ROOT/openclaw-log" QUEUE_REVIEW_COOLDOWN_MIN=0 RUN_ACTIVITY_WINDOW_SEC=300 bash "$PRECHECK_SCRIPT" > "$TMP_ROOT/precheck-$scenario.log" 2>&1
  else
    PATH="$TMP_ROOT/bin:$PATH" WORKSPACE="$TMP_ROOT/workspace" PRECHECK_STATE="$TMP_ROOT/workspace/framework/board-review/PRECHECK_STATE.json" PRECHECK_FAILURE_STATE="$TMP_ROOT/workspace/framework/board-review/PRECHECK_FAILURE_STATE.json" OPENCLAW_MOCK_LOG_DIR="$TMP_ROOT/openclaw-log" QUEUE_REVIEW_COOLDOWN_MIN=0 RUN_ACTIVITY_WINDOW_SEC=300 bash "$PRECHECK_SCRIPT" "$mode" > "$TMP_ROOT/precheck-$scenario.log" 2>&1
  fi
}

test_actionability_state() {
  setup_fixture
  run_precheck labels --dry-run
  local state="$TMP_ROOT/workspace/framework/board-review/PRECHECK_STATE.json"
  assert_json "$state" '.actionableIssues | length == 1' "deduplicates live actionable issues"
  assert_json "$state" '.actionableIssues[0].repo == "hendrixAIDev/churn_copilot_hendrix"' "records actionable repo"
  assert_json "$state" '.actionableIssues[0].number == 101' "records actionable number"
  assert_json "$state" 'has("openIssues") | not' "removes stale openIssues"
  assert_json "$state" '.openIssuesByRepo["hendrixAIDev/churn_copilot_hendrix"] == [101,202]' "keeps open issue inventory separate"
}

test_prompt_routing() {
  setup_fixture
  run_precheck prompts live
  sleep 1
  local wake_count
  wake_count="$(find "$TMP_ROOT/openclaw-log" -name "wake-*.txt" | wc -l | tr -d " ")"
  [[ "$wake_count" == "2" ]] && pass "routes ChurnPilot and Framework independently" || fail "routes ChurnPilot and Framework independently"
  assert_contains "$TMP_ROOT/openclaw-log/wake-0.txt" "Product context:" "wake prompt includes product context block"
  assert_contains "$TMP_ROOT/openclaw-log/wake-0.txt" "Product: ChurnPilot" "ChurnPilot prompt includes product"
  assert_contains "$TMP_ROOT/openclaw-log/wake-0.txt" "Product state: framework/board-review/state/churnpilot.md" "ChurnPilot prompt includes state path"
  assert_contains "$TMP_ROOT/openclaw-log/wake-0.txt" "Task queue: projects/churn_copilot/plans/task-queue.yaml" "ChurnPilot prompt includes queue path"
  assert_contains "$TMP_ROOT/openclaw-log/wake-1.txt" "Product: Framework" "Framework prompt includes product"
  assert_contains "$TMP_ROOT/openclaw-log/wake-1.txt" "Product state: framework/board-review/state/framework.md" "Framework prompt includes state path"
  assert_contains "$TMP_ROOT/openclaw-log/wake-1.txt" "Task queue: framework/plans/task_queue/tasks.yaml" "Framework prompt includes queue path"
}

test_runlocks() {
  setup_fixture
  write_gh_mock prompts
  sleep 30 & live_pid=$!
  printf '{"startedAt":"2026-05-15T00:00:00Z","startedEpoch":%s,"sessionId":"46dfba9a-c319-41b9-b226-393a7ea10d1a","product":"churnpilot","pid":%s,"logFile":"%s/live.log"}\n' "$(date +%s)" "$live_pid" "$TMP_ROOT" > "$TMP_ROOT/workspace/framework/board-review/runlocks/cto-churnpilot.lock"
  : > "$TMP_ROOT/live.log"
  PATH="$TMP_ROOT/bin:$PATH" WORKSPACE="$TMP_ROOT/workspace" PRECHECK_STATE="$TMP_ROOT/workspace/framework/board-review/PRECHECK_STATE.json" PRECHECK_FAILURE_STATE="$TMP_ROOT/workspace/framework/board-review/PRECHECK_FAILURE_STATE.json" OPENCLAW_MOCK_LOG_DIR="$TMP_ROOT/openclaw-log" bash "$PRECHECK_SCRIPT" "" > "$TMP_ROOT/precheck-lock-live.log" 2>&1
  kill "$live_pid" 2>/dev/null || true
  wait "$live_pid" 2>/dev/null || true
  wake_count="$(find "$TMP_ROOT/openclaw-log" -name "wake-*.txt" 2>/dev/null | wc -l | tr -d " ")"
  [[ "$wake_count" == "1" ]] && pass "live run lock prevents duplicate wake" || fail "live run lock prevents duplicate wake"

  setup_fixture
  write_gh_mock prompts
  printf '{"startedAt":"2026-05-15T00:00:00Z","startedEpoch":1,"sessionId":"46dfba9a-c319-41b9-b226-393a7ea10d1a","product":"churnpilot","pid":999999,"logFile":"/tmp/no-such-log"}\n' > "$TMP_ROOT/workspace/framework/board-review/runlocks/cto-churnpilot.lock"
  PATH="$TMP_ROOT/bin:$PATH" WORKSPACE="$TMP_ROOT/workspace" PRECHECK_STATE="$TMP_ROOT/workspace/framework/board-review/PRECHECK_STATE.json" PRECHECK_FAILURE_STATE="$TMP_ROOT/workspace/framework/board-review/PRECHECK_FAILURE_STATE.json" OPENCLAW_MOCK_LOG_DIR="$TMP_ROOT/openclaw-log" bash "$PRECHECK_SCRIPT" "" > "$TMP_ROOT/precheck-lock-dead.log" 2>&1
  wake_count="$(find "$TMP_ROOT/openclaw-log" -name "wake-*.txt" 2>/dev/null | wc -l | tr -d " ")"
  [[ "$wake_count" == "2" && ! -f "$TMP_ROOT/workspace/framework/board-review/runlocks/cto-churnpilot.lock" ]] && pass "dead run lock is cleared" || fail "dead run lock is cleared"
}

main() {
  test_actionability_state
  test_prompt_routing
  test_runlocks
  printf "\n%s passed, %s failed\n" "$PASS_COUNT" "$FAIL_COUNT"
  [[ "$FAIL_COUNT" -eq 0 ]]
}

main "$@"
