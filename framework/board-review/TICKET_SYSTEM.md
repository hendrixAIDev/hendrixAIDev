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
status:new → status:in-progress → status:new → ... → status:done (CLOSED)
```

| Status | Meaning | Who sets it |
|--------|---------|-------------|
| `status:new` | Needs CTO triage / next-step decision | CTO, or sub-agent when its pass ends |
| `status:in-progress` | Sub-agent working | CTO before dispatch |
| `status:review` | Review needed | Optional, CTO-controlled |
| `status:verification` | Validation needed | Optional, CTO-controlled |
| `status:cto-review` | Final CTO check | Optional, CTO-controlled |
| `status:done` | Closed | CTO only |
| `status:blocked` | Waiting on dependency | CTO only |
| `status:needs-jj` | CEO decision required | CTO only |

**Key rule:** CTO sets `status:in-progress` before dispatch so precheck does not double-wake while work is active. When the sub-agent finishes, it normally returns the ticket to `status:new` so CTO can decide the next step.

**Priority:** `priority:high` · `priority:medium` · `priority:low`

---

## Dependencies

Tickets with a `### Dependencies` section listing `- [ ] #N` issue refs use GitHub's native tracked-issues.

**Unblocking is automatic:** A GitHub Action (`unblock-dependencies.yml`) fires when any issue closes. It checks all `status:blocked` tickets — if ALL their deps are now closed, it sets them to `status:new` with a comment.

**Template location:** `framework/board-review/workflows/unblock-dependencies.yml` — install this in every new repo's `.github/workflows/`.

---

## Sub-Agent Label Rules (MANDATORY)

**Every sub-agent MUST update the ticket label before exiting.**

### Default success rule

When your work pass is complete:
1. Set the ticket to `status:new`
2. Post a comment with:
   - what you did
   - what result you got
   - what validation you performed, if any
   - what you recommend as the next step
3. Leave the issue **OPEN**

This wakes CTO back up to decide the next move.

### Failure rule

If your work fails, is rejected, or you cannot complete the task:
1. Set `status:new` on the ticket
2. Post a comment explaining what failed and why
3. Leave the issue **OPEN**

### Exception rule

Only set a more specific status such as `status:review`, `status:verification`, or `status:cto-review` if the CTO explicitly instructed you to do that in the dispatch note.

### How to update labels:

```bash
# Remove old label, add new one
gh issue edit <NUMBER> --repo <OWNER/REPO> --remove-label "status:in-progress" --add-label "status:new"
```

### Completion checklist (all roles):

- [ ] Work completed (or failure documented)
- [ ] Completion/failure comment posted on GitHub issue
- [ ] Label updated before exit
- [ ] Issue left **OPEN** (only CTO closes issues)

---

## Branch & Deployment Rules

These rules apply when the chosen next step involves implementation work.

| Action | Who | Notes |
|--------|-----|-------|
| Work in isolated worktree | Engineer | `/tmp/wt/{repo-short}-{ticket-num}`, branch `fix/{repo-short}-{ticket-num}` |
| Review code in worktree | Reviewer if CTO requests review | `git diff origin/experiment..HEAD` inside the worktree |
| Run verification in worktree or deployed env | Validation role chosen by CTO | Match the validation plan |
| Merge worktree branch → `experiment` | Validation role chosen by CTO | Only if that validation pass is authorized to merge |
| Test on experiment endpoint | Validation role chosen by CTO | Browser automation, never localhost, when deployed verification is required |
| Clean up worktree | Validation role that finishes the deployed pass | `git worktree remove /tmp/wt/{name} --force` when done |
| Close tickets | CTO only | Only after required validation evidence exists |
| Merge `experiment` → `main` | CEO (JJ) only | Production deployment |

There is no universal required implementation pipeline. CTO chooses the next step. These worktree and deployment rules apply only when the chosen workflow needs them.

---

## Engineer Handoff Gate (MANDATORY)

Before an engineer returns a ticket to CTO, the ticket comment must explicitly include:

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

If this handoff comment is missing, incomplete, or does not mention both sync-from-`experiment` and localhost verification, the next CTO pass should treat the handoff as incomplete and send it back for correction instead of advancing.

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

## Closing Rule

Sub-agents never close tickets.

Before CTO closes a ticket, the ticket must contain the validation evidence CTO decided was required for that ticket.

## PRECHECK_STATE.json — Hands Off

Only the automation precheck reads/writes this file. Fix labels on GitHub to unstick the pipeline.
