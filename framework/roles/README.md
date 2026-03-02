# Roles

Role-based agent system. Each dispatched sub-agent gets: cached role + shared overlay + role-specific overlay.

## Active Roles

| Role | `cached/` | `overlays/` |
|------|-----------|-------------|
| **CTO** | `cto.md` | `cto-overlay.md` |
| **Backend Architect** | `backend-architect.md` | `backend-architect-overlay.md` |
| **Frontend Engineer** | `frontend-engineer.md` | `frontend-engineer-overlay.md` |
| **Code Reviewer** | `code-reviewer.md` | `code-review-overlay.md` |
| **QA Engineer** | `qa-engineer.md` | `qa-overlay.md` |

All roles also receive `overlays/shared-overlay.md` (tech stack, projects, tools).

## How It Works

1. CTO dispatches via `skills/dispatch-agent/` with `--role <name>`
2. Dispatch script composes prompt from `skills/dispatch-agent/references/<name>.md`
3. Template tells sub-agent to read: TICKET_SYSTEM → CONVENTIONS → cached role → shared overlay → role overlay
4. Sub-agent executes, updates ticket label, exits

## Key Files

- **CONVENTIONS.md** — Rules for ALL sub-agents (commits, lint, testing, docs)
- **overlays/shared-overlay.md** — Common context (tech stack, Supabase, Streamlit, project list)
