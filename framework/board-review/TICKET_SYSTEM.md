# Ticket System — Sub-Agent Reference

**Audience:** All sub-agents.  

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

**Source of truth:** `framework/board-review/REPOS.conf` — one repo per line.

**Update issues via CLI:**
```bash
# Add comment
gh issue comment 42 --repo hendrixAIDev/[repo] --body "..."

# Update labels
gh issue edit 42 --repo hendrixAIDev/[repo] --add-label "status:in-progress"
```

---

## Status Flow

```
status:new → status:in-progress → status:review → status:verification → status:cto-review → status:done (CLOSED)
```

| Status | Meaning | Who sets it |
|--------|---------|-------------|
| `status:new` | Needs triage & dispatch | CTO, or any agent on failure |
| `status:in-progress` | Sub-agent working (any phase) | CTO (before every dispatch) |
| `status:review` | Code review needed | Engineer (when done coding) |
| `status:verification` | QA needed | Code reviewer (on approve) |
| `status:cto-review` | Final approval | QA (on pass) |
| `status:done` | Closed | CTO (on approve) |
| `status:blocked` | Waiting on dependency | CTO (during triage) |
| `status:needs-jj` | CEO decision required | CTO only (during triage) |

**Key rule:** CTO sets `status:in-progress` BEFORE every dispatch (Phases 1, 2, 3). This prevents the precheck from seeing the ticket as actionable and double-dispatching.

**Priority:** `priority:high` · `priority:medium` · `priority:low`

---

## Dependencies

Tickets with a `### Dependencies` section listing `- [ ] #N` issue refs use GitHub's native tracked-issues.

**Unblocking is automatic:** A GitHub Action (`unblock-dependencies.yml`) fires when any issue closes. It checks all `status:blocked` tickets — if ALL their deps are now closed, it sets them to `status:new` with a comment.

**Template location:** `framework/board-review/workflows/unblock-dependencies.yml` — install this in every new repo's `.github/workflows/`.

---

## Sub-Agent Label Rules (MANDATORY)

**Every sub-agent MUST update the ticket label before exiting.** This is how the pipeline knows what to do next.

### On Success — set the next status:

| Your Role | You receive | On success, set |
|-----------|------------|-----------------|
| Engineer | `status:in-progress` | `status:review` |
| Code Reviewer | `status:in-progress` | `status:verification` |
| QA Engineer | `status:in-progress` | `status:cto-review` |

### On Failure — reset to `status:new`:

If your work fails, is rejected, or you cannot complete the task:
1. Set `status:new` on the ticket
2. Post a comment explaining what failed and why
3. Leave the issue **OPEN**

The CTO will pick it up on the next triage pass and decide what to do.

### How to update labels:

```bash
# Remove old label, add new one
gh issue edit <NUMBER> --repo <OWNER/REPO> --remove-label "status:in-progress" --add-label "status:review"
```

### Completion checklist (all roles):

- [ ] Work completed (or failure documented)
- [ ] Completion/failure comment posted on GitHub issue
- [ ] Label updated to next status (success) or `status:new` (failure)
- [ ] Issue left **OPEN** (only CTO closes issues)

---

## Branch & Deployment Rules

| Action | Who | Notes |
|--------|-----|-------|
| Work in isolated worktree | Engineer | `/tmp/wt/{repo-short}-{ticket-num}`, branch `fix/{repo-short}-{ticket-num}` |
| Review code in worktree | Code Reviewer | `git diff origin/experiment..HEAD` inside the worktree |
| Review tests in worktree | QA Engineer | Before merging |
| Merge worktree branch → `experiment` | QA Engineer | Only after code review + test review pass |
| Test on experiment endpoint | QA Engineer | Browser automation, never localhost |
| Clean up worktree | QA Engineer | `git worktree remove /tmp/wt/{name} --force` after successful merge |
| Close tickets | CTO only | After QA passes |
| Merge `experiment` → `main` | CEO (JJ) only | Production deployment |

**Flow:** Engineer (worktree at `/tmp/wt/`) → Code Review (same worktree) → QA (review in worktree → merge to experiment → test on experiment → remove worktree) → CTO Review → Done

---

## Engineer Handoff Gate (MANDATORY)

Before an engineer sets `status:review`, the ticket comment must explicitly include:

- confirmation the branch was synced/rebased from latest `origin/experiment`
- confirmation the fix was tested locally on `http://localhost:<port>` (any localhost port is acceptable)
- short note on what was verified
- relevant tests that passed

**Required template:**

```markdown
**Engineer handoff checklist:**
- [x] Synced/rebased from latest `origin/experiment`
- [x] Tested locally on `http://localhost:8511` (or any localhost port actually used)
- [x] Verified: <feature / bugfix description>
- [x] Tested edge case(s): <notes>
- [x] Relevant tests passed: <unit / integration / e2e>
- [x] Ready for code review
```

If this handoff comment is missing, incomplete, or does not mention both sync-from-`experiment` and localhost verification, the code reviewer should reject the ticket back to `status:new` immediately instead of doing a full review.

**Suggested rejection comment:**

```markdown
❌ Review rejected: engineer handoff incomplete.

Before code review, the engineer must post a handoff comment confirming:
- branch synced/rebased from latest `origin/experiment`
- local verification completed on `http://localhost:<port>` (any localhost port is acceptable)
- what was tested
- relevant tests passed

Resetting to `status:new` so an engineer can complete the required pre-review validation.
```

---

## PRECHECK_STATE.json — Hands Off

Only the automation precheck reads/writes this file. Fix labels on GitHub to unstick the pipeline.
