# Engineering Framework

Automated board review, ticket management, and AI-agent coordination.

## Structure

```
board-review/       # 7-phase automated pipeline (status-driven)
  BOARD_REVIEW_TRIGGER.md       # CTO execution guide
  CTO_PROMPT.md                 # Stateless CTO session prompt
  TICKET_SYSTEM.md              # Ticket labels, status workflow
  REPOS.conf                    # Monitored repos (single source of truth)
  SUBAGENT_BROWSER_PROFILE.md   # Browser profile allocation for sub-agents
  GITHUB_SCREENSHOT_UPLOAD.md   # Screenshot upload via GitHub API
  scripts/dispatch.sh           # Sub-agent dispatch (isolated cron jobs)
  workflows/                    # GitHub Actions (dependency unblocking)

roles/              # Sub-agent role definitions and overlays
  CONVENTIONS.md            # Engineering playbook
  cached/                   # Pre-built role prompts
  overlays/                 # Context overlays (shared tools, project-specific)

evolver/            # EvoMap integration — solution capsule matching
  capsules/                 # Local capsule database (22 validated solutions)
  scripts/publish-capsule.sh

tools/              # Shared engineering tools
  smoke_test.py             # Deploy smoke test (HTTP liveness + SCHP)
  code_search.py            # SQLite FTS5 code search
  generate_dependency_graph.py
```

## Architecture

```
OS cron (5 min) → precheck.sh (bash, zero LLM)
  → openclaw cron add (one-shot CTO session)
    → CTO dispatches via dispatch.sh (isolated sub-agents)
      → sub-agents update ticket labels
        → precheck detects changes → next CTO pass
```

**Key principles:**
- Status-driven workflow — ticket labels are the single shared state
- Stateless CTO sessions — dispatch and exit, no polling
- Zero-LLM precheck — OS cron + bash, no token waste
- Event-driven dependencies — GitHub Actions auto-unblock on issue close
