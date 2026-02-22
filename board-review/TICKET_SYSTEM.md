# Ticket System — Sub-Agent Reference

**Audience:** All sub-agents.  
**MANDATORY FIRST:** Read `PROJECT_STRUCTURE.md`.

---

## ⛔ Critical Rules

### 1. Never Close Issues
Your final action: update the status label and **STOP**. Only CTO closes issues.

### 2. Safe Commit Messages
Never use auto-close keywords (`Fix #N`, `Closes #N`, `Resolve #N`).  
Use: `ref #N`, `relates to #N`, `[#N]`.

### 3. Failure → `status:new`
If your work fails at any phase, set the ticket back to `status:new` and add a comment explaining what went wrong. The CTO will re-triage.

---

## Repos

| Scope | Repo |
|-------|------|
| General / Framework | `hendrixAIDev/hendrixAIDev` |
| ChurnPilot | `hendrixAIDev/churn_copilot_hendrix` |
| StatusPulse | `hendrixAIDev/statuspulse` |

---

## Status Flow

```
status:new → status:in-progress → status:review → status:verification → status:cto-review → status:done (CLOSED)
```

| Status | Meaning | Who sets it |
|--------|---------|-------------|
| `status:new` | Needs triage & dispatch | CTO, or any agent on failure |
| `status:in-progress` | Engineer working | CTO (on dispatch) |
| `status:review` | Code review needed | Engineer (when done) |
| `status:verification` | QA needed | Code reviewer (on approve) |
| `status:cto-review` | Final approval | QA (on pass) |
| `status:done` | Closed | CTO (on approve) |
| `status:blocked` | Waiting on dependency | CTO (during triage) |
| `status:needs-jj` | CEO decision required | CTO only (during triage) |

**Priority:** `priority:high` · `priority:medium` · `priority:low`

---

## Dependencies

Tickets with a `### Dependencies` section listing `- [ ] #N` issue refs use GitHub's native tracked-issues.

**Unblocking is automatic:** A GitHub Action (`unblock-dependencies.yml`) fires when any issue closes. It checks all `status:blocked` tickets — if ALL their deps are now closed, it sets them to `status:new` with a comment.

**Template location:** `framework/board-review/workflows/unblock-dependencies.yml` — install this in every new repo's `.github/workflows/`.

---

## Sub-Agent Completion Checklist

Before setting `status:review`:
- [ ] All requirements implemented
- [ ] Tests written and passing
- [ ] Tested on local server (UI changes visible, no console errors)
- [ ] Documentation updated if needed
- [ ] Completion comment posted on GitHub issue
- [ ] Label updated to `status:review`
- [ ] Issue left **OPEN**

---

## QA Requirements

QA **must** use browser automation on the deployed experiment endpoint. Code review alone is NOT sufficient.

- Review code changes, check for missing tests
- Push to `experiment` branch if code looks good
- Navigate real user flow on experiment endpoint → confirm fix
- Screenshot/snapshot evidence in QA report
- See `framework/roles/overlays/qa-overlay.md` for full standards

---

## Deployment Authority

| Action | Who |
|--------|-----|
| Push to `experiment` | QA (after code review) |
| Close tickets | CTO only |
| Merge to `main` | CEO (JJ) only |

---

## PRECHECK_STATE.json — Hands Off

Only the automation precheck reads/writes this file. Fix labels on GitHub to unstick the pipeline.
