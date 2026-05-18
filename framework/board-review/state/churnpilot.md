# ChurnPilot State

**Purpose:** Preserve compact cross-run continuity for the ChurnPilot product CTO session.

**What this covers:**
- Product identity and routing
- Current result, blockers, and active dispatches
- Durable handoff notes for future ChurnPilot CTO wakes

## Routing

| Field | Value |
|---|---|
| Product | ChurnPilot |
| Slug | churnpilot |
| Session key | `agent:main:churnpilot-cto` |
| Session id | resolved at runtime |
| Repos | `hendrixAIDev/churn_copilot_hendrix` |
| Primary README | `projects/churn_copilot/README.md` |
| Task queue | `projects/churn_copilot/plans/task-queue.yaml` |
| Updated by | main-session |

## Current State

| Field | Value |
|---|---|
| Last run at | 2026-05-17T15:46:00-07:00 |
| Last result | CP #245 experiment QA retry passed on commit `ea47e6c8149144854954697f21c0a40cf01b7904`: experiment landing validated with split hero, CTAs, payment-free/trust/legal messaging, mobile layout, Chinese localization after explicit localized-body wait, and GitHub Actions run `26004798237` passed Unit Tests and E2E Browser Tests. CTO accepted CP #245, marked it `status:done`, and closed the issue. CP #243 remains `status:needs-jj` for production promotion approval. |

## Current Blockers

- CP #243: production still shows old session banner because main is behind experiment; needs JJ approval for production promotion.

## Active Dispatches

- None.

## Handoff Notes

- Validate board-review QA against the experiment deployment unless JJ explicitly approves production validation.
- CP #244 is accepted and closed on `origin/experiment`; no further CP #244 dispatch is needed unless production promotion or a fresh regression opens a new issue.
- CP #245 is accepted and closed on `origin/experiment`; no further CP #245 dispatch is needed unless production promotion or a fresh regression opens a new issue.
- CP #188, #189, and #190 are historical context only and should not trigger new heartbeat alerts.
