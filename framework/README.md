# Framework

Operational engine for the Hendrix/JJ AI-assisted development workflow.

## Structure

```
framework/
├── PROJECTS.md              — Single source of truth for project status
├── board-review/            — Automated ticket pipeline
│   ├── BOARD_REVIEW.md      — CTO 6-phase workflow (source of truth)
│   ├── CTO_PROMPT.md        — One-shot CTO session bootstrap
│   ├── TICKET_SYSTEM.md     — Status labels, sub-agent rules
│   ├── BOARD_REVIEW_STATUS.md — Current pipeline state
│   ├── REPOS.conf           — Repos scanned by precheck
│   └── PRECHECK_STATE.json  — Precheck automation state
├── roles/                   — Role-based agent system
│   ├── CONVENTIONS.md       — Rules for ALL sub-agents (commits, lint, testing)
│   ├── cached/              — Agent role definitions (5 active)
│   └── overlays/            — Context overlays (shared + role-specific)
└── evolver/                 — EvoMap capsule system
```

## Key Files

| File | Audience | Purpose |
|------|----------|---------|
| `PROJECTS.md` | Everyone | Project status, repos, URLs |
| `board-review/BOARD_REVIEW.md` | CTO session | Full pipeline workflow |
| `board-review/TICKET_SYSTEM.md` | All sub-agents | Label rules, status flow |
| `roles/CONVENTIONS.md` | All sub-agents | Commit, lint, test, doc rules |
| `roles/overlays/shared-overlay.md` | All sub-agents | Tech stack, projects, tools |

## Active Roles

| Role | Cached | Overlay | Dispatch |
|------|--------|---------|----------|
| CTO | `cached/cto.md` | `overlays/cto-overlay.md` | Board review cron |
| Backend Architect | `cached/backend-architect.md` | `overlays/backend-architect-overlay.md` | `--role backend-architect` |
| Frontend Engineer | `cached/frontend-engineer.md` | `overlays/frontend-engineer-overlay.md` | `--role frontend-engineer` |
| Code Reviewer | `cached/code-reviewer.md` | `overlays/code-review-overlay.md` | `--role code-reviewer` |
| QA Engineer | `cached/qa-engineer.md` | `overlays/qa-overlay.md` | `--role qa` |

Dispatch via `skills/dispatch-agent/` — see that skill's SKILL.md for usage.
