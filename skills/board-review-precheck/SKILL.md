---
name: board-review-precheck
description: Zero-LLM board review pre-check. Runs every 1 minute via OS cron to scan GitHub repos for actionable issue labels and detect stale WIP tickets. Triggers the Opus Board Review CTO cron when work is found, resets stale tickets (>45 min no activity) back to status:new, and posts hourly Slack summaries when quiet. Uses gh CLI + openclaw CLI directly — no LLM tokens consumed.
---

# Board Review Pre-Check

Lightweight GitHub label scanner + watchdog that runs the board review automation pipeline with zero LLM tokens.

## What It Does

Every 1 minute (via OS crontab):

**1. Watchdog** (`watchdog.sh`): Checks all WIP tickets (`status:in-progress`, `status:review`, `status:verification`, `status:cto-review`) across all repos. If last comment is >45 min old, resets to `status:new` with a comment explaining the reset. Catches ghost tickets where sub-agents died or were never spawned.

**2. Precheck** (`precheck.sh`): Scans repos for actionable labels (`status:new`, `status:review`, `status:verification`, `status:cto-review`). If found, wakes the mapped product CTO session. Posts hourly Slack summaries when quiet.

**Trigger rule:** Any issue activity (label changes, comments, reopens, closes, new issues) triggers the Opus CTO. This is broader than just checking for actionable labels — the CTO decides what to act on.

## Usage

Run directly (for testing):
```bash
bash scripts/precheck.sh          # live run
bash scripts/precheck.sh --dry-run # see what would happen
```

### As a Cron Job

Replace the existing Haiku pre-check cron with a `systemEvent` that runs the script:

```
cron(action="update", jobId="<precheck-cron-id>", patch={
  "payload": {
    "kind": "systemEvent",
    "text": "bash skills/board-review-precheck/scripts/precheck.sh"
  },
  "sessionTarget": "main"
})
```

Or better — set up as an OS-level cron/launchd job that runs the script directly, bypassing OpenClaw's cron scheduler entirely.

## Configuration

All config via environment variables (with sensible defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKSPACE` | `~/.openclaw/workspace` | Workspace root |
| `PRECHECK_STATE` | `$WORKSPACE/framework/board-review/PRECHECK_STATE.json` | State file path |
| `OPUS_CRON_ID` | `9c1c2dd1-...` | Board Review CTO cron job ID |
| `SLACK_CHANNEL` | `C0ABYMAUV3M` | Slack channel for summaries |
| `SUMMARY_INTERVAL_MIN` | `60` | Minutes between hourly summaries |
| `OPUS_COOLDOWN_MIN` | `5` | Min minutes between Opus CTO triggers (prevents spam) |

## Dependencies

- `gh` CLI (authenticated)
- `jq`
- `openclaw` CLI (for `cron run` and `message send`)

## State File

Reads/writes `PRECHECK_STATE.json`:
```json
{
  "lastCheckTime": "ISO-8601",
  "lastSummaryTime": "ISO-8601",
  "lastOpusTrigger": "ISO-8601",
  "consecutiveSkips": 0
}
```

## Why This Exists

The previous Haiku LLM pre-check accumulated 90k+ tokens per day because:
1. OpenClaw reused the same session across runs (sticky sessions)
2. Each 5-min run added to conversation history (O(n²) token growth)
3. The system prompt included 41 skill descriptions (13k chars) the pre-check never needed

This script does the same job with zero LLM tokens.
