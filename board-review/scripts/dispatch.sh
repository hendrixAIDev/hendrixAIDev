#!/usr/bin/env bash
# dispatch.sh — Spawn an isolated one-shot agent session
#
# Usage:
#   dispatch.sh --name "eng-sp26-migration" --message "Fix the migration..."
#   dispatch.sh --name "qa-sp18-alerts" --model sonnet --thinking low --message "Run QA..."
#   dispatch.sh --name "review-sp15" --timeout 300 --message "Review PR..."
#
# Options:
#   --name      <name>      Job name (required)
#   --message   <text>      Task prompt (required)
#   --model     <alias>     Model alias or full name (default: anthropic/claude-sonnet-4-6)
#   --thinking  <level>     Thinking level (default: low)
#   --timeout   <seconds>   Timeout in seconds (default: 600)
#   --delay     <duration>  Delay before start (default: 1m)
#
# The spawned agent:
#   - Runs in full isolation (no callbacks, no announcements)
#   - Self-deletes after completion
#   - Should update GitHub ticket labels when done

set -euo pipefail

# Defaults
MODEL="anthropic/claude-sonnet-4-6"
THINKING="low"
TIMEOUT=600
DELAY="1m"
NAME=""
MESSAGE=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)     NAME="$2"; shift 2 ;;
    --message)  MESSAGE="$2"; shift 2 ;;
    --model)    MODEL="$2"; shift 2 ;;
    --thinking) THINKING="$2"; shift 2 ;;
    --timeout)  TIMEOUT="$2"; shift 2 ;;
    --delay)    DELAY="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$NAME" || -z "$MESSAGE" ]]; then
  echo "Error: --name and --message are required" >&2
  exit 1
fi

exec openclaw cron add \
  --name "$NAME" \
  --at "$DELAY" \
  --session isolated \
  --delete-after-run \
  --model "$MODEL" \
  --thinking "$THINKING" \
  --timeout-seconds "$TIMEOUT" \
  --no-deliver \
  --message "$MESSAGE" \
  --json
