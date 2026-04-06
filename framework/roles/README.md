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
| **Product Readiness Auditor** | `product-readiness-auditor.md` | `product-readiness-overlay.md` |
| **User Journey Auditor** | `user-journey-auditor.md` | `user-journey-overlay.md` |
| **Trust & Risk Auditor** | `trust-risk-auditor.md` | `trust-risk-overlay.md` |
| **Launch Positioning Reviewer** | `launch-positioning-reviewer.md` | `launch-positioning-overlay.md` |

All roles also receive `overlays/shared-overlay.md` (tech stack, projects, tools).

## How It Works

1. CTO dispatches via `skills/dispatch-agent/` with `--role <name>`
2. Dispatch script composes prompt from `skills/dispatch-agent/references/<name>.md`
3. Template tells sub-agent to read: TICKET_SYSTEM → CONVENTIONS → cached role → shared overlay → role overlay
4. Sub-agent executes, updates ticket label, exits

## Key Files

- **CONVENTIONS.md** — Rules for ALL sub-agents (commits, lint, testing, docs)
- **overlays/shared-overlay.md** — Common context (tech stack, Supabase, Streamlit, project list)

## Launch Analysis Roles

These four roles are intended for pre-public-launch analysis of ChurnPilot:

- **Product Readiness Auditor** — Overall go / conditional go / no-go assessment
- **User Journey Auditor** — End-to-end friction audit from a real user's perspective
- **Trust & Risk Auditor** — Trust, credibility, safety, and reputational risk review
- **Launch Positioning Reviewer** — Messaging, value proposition, and first-impression clarity review

Recommended analysis order:
1. Product Readiness Auditor
2. User Journey Auditor
3. Trust & Risk Auditor
4. Launch Positioning Reviewer

## Remote Roles

For roles not cached locally, fetch from **wshobson/agents** repo:

```bash
gh api repos/wshobson/agents/contents/plugins/<plugin>/agents/<role>.md --jq '.content' | base64 -d
```

**Available marketing/content roles:**
- `content-marketing/agents/content-marketer.md` — Elite content marketing strategist
- `content-marketing/agents/search-specialist.md` — Search/SEO specialist
- `seo-content-creation/agents/seo-content-writer.md` — SEO content writer
- `seo-content-creation/agents/seo-content-planner.md` — Content strategy planner
- `startup-business-analyst/agents/startup-analyst.md` — Startup business analysis

**Usage:** Fetch the role content and inject it into the sub-agent's system prompt. Do not cache locally — always fetch fresh from remote.
