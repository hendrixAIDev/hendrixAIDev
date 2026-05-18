# Framework

**Purpose:** Describe the shared execution framework for the Hendrix/JJ AI-assisted development workflow.

**What this covers:**
- Board-review automation structure
- Role and dispatch documentation
- Framework planning and task-queue files
- Key files maintainers should know before changing the framework

## Structure

```
framework/
├── PROJECTS.md              — Single source of truth for project status
├── board-review/            — Automated ticket pipeline
│   ├── BOARD_REVIEW.md      — CTO 6-phase workflow (source of truth)
│   ├── CTO_PROMPT.md        — One-shot CTO session bootstrap
│   ├── PM_PROMPT.md         — Persistent PM discovery wake template
│   ├── TICKET_SYSTEM.md     — Status labels, sub-agent rules
│   ├── REPOS.conf           — Repos scanned by precheck
│   ├── PRECHECK_STATE.json  — Precheck automation state
│   ├── state/               — Per-product CTO continuity state in Markdown
│   └── tests/               — Offline contract tests for routing/state invariants
├── roles/                   — Role-based agent system
│   ├── CONVENTIONS.md       — Shared role practices
│   ├── cached/              — Agent role definitions (5 active)
│   └── overlays/            — Context overlays (shared + role-specific)
├── plans/                   — Framework PM planning artifacts and task queue
│   ├── README.md            — PM session + planning file index
│   └── task_queue/tasks.yaml — Framework PM/CTO intake queue
└── evolver/                 — EvoMap capsule system
```

## Key Files

| File | Audience | Purpose |
|------|----------|---------|
| `PROJECTS.md` | Everyone | Project status, repos, URLs |
| `board-review/BOARD_REVIEW.md` | CTO session | Full pipeline workflow |
| `board-review/PRECHECK_STATE.json` | Precheck automation | Runtime scan/cache state |
| `board-review/state/*.md` | Product CTO sessions | Product-owned cross-run continuity |
| `board-review/TICKET_SYSTEM.md` | All sub-agents | Label rules, status flow |
| `board-review/tests/run.sh` | Maintainers | Required offline contract test after board-review framework changes |
| `roles/CONVENTIONS.md` | All role-based agents | Navigation, scope, verification, docs, Git safety, and handoff practice |
| `roles/overlays/shared-overlay.md` | All sub-agents | Tech stack, projects, tools |
| `plans/README.md` | Framework PM/CTO | Planning artifacts and PM session registry |
| `plans/task_queue/tasks.yaml` | Framework PM/CTO | Framework task queue scanned by board-review precheck |

## Active Roles

| Role | Cached | Overlay | Prompt ownership |
|------|--------|---------|------------------|
| CTO | `cached/cto.md` | `overlays/cto-overlay.md` | Board review wake prompt |
| Backend Architect | `cached/backend-architect.md` | `overlays/backend-architect-overlay.md` | CTO-authored dispatch prompt |
| Frontend Engineer | `cached/frontend-engineer.md` | `overlays/frontend-engineer-overlay.md` | CTO-authored dispatch prompt |
| Code Reviewer | `cached/code-reviewer.md` | `overlays/code-review-overlay.md` | CTO-authored dispatch prompt |
| QA Engineer | `cached/qa-engineer.md` | `overlays/qa-overlay.md` | CTO-authored dispatch prompt |

Dispatch via `skills/dispatch-agent/` with a complete `--message` or `--message-file`; dispatch-agent does not compose role prompts.
