# Ticket System - Sub-Agent Reference

**Purpose:** Define the narrow GitHub issue responsibilities for sub-agents working under the board-review CTO workflow.

**What this covers:**
- Sub-agent issue safety rules
- Required evidence comments
- Returning tickets to `status:new`
- Branch, worktree, and deployment boundaries
- Engineer implementation handoff requirements

**Audience:** All sub-agents.

For CTO triage, planning, validation decisions, and closure rules, read `framework/board-review/BOARD_REVIEW.md`.

---

## Sub-Agent Contract

Sub-agents execute one assigned pass. They do not own the ticket lifecycle.

Rules:

1. Follow the CTO's dispatch prompt and assigned scope.
2. Post evidence on the GitHub issue before exiting.
3. Return the ticket to `status:new` unless the CTO explicitly instructed a different final label.
4. Leave the issue open.
5. Never close issues.
6. Never edit `PRECHECK_STATE.json`.

`status:new` does not mean the work is accepted or finished. It means the CTO must decide the next step.

---

## Critical Safety Rules

### Never Close Issues

Only CTO closes issues. A sub-agent pass is not complete until the issue has a completion or failure comment and the status label has been updated away from `status:in-progress`.

### Use Safe Commit Messages

Never use auto-close keywords:

- `Fix #N`
- `Fixes #N`
- `Closes #N`
- `Resolve #N`
- `Resolves #N`

Use safe references instead:

- `ref #N`
- `relates to #N`
- `[#N]`

### Return Failures To CTO

If the assigned pass fails, is blocked, or cannot be completed, post what happened and return the ticket to `status:new`. The CTO will re-triage.

---

## Repos

**Source of truth:** `framework/board-review/REPOS.conf` - one repo per line.

Common issue commands:

```bash
# Add a comment
gh issue comment 42 --repo hendrixAIDev/<repo> --body "..."

# Return the ticket to CTO
gh issue edit 42 --repo hendrixAIDev/<repo> --remove-label "status:in-progress" --add-label "status:new"

# Verify labels before exit
gh issue view 42 --repo hendrixAIDev/<repo> --json labels | jq -r '.labels[].name'
```

---

## Status Labels

Normal handoff loop:

```text
status:new -> status:in-progress -> status:new -> ... -> status:done (closed by CTO)
```

| Status | Meaning | Who sets it |
|--------|---------|-------------|
| `status:new` | CTO must triage or decide the next step | CTO, or sub-agent at pass end |
| `status:in-progress` | A sub-agent pass is active | CTO before dispatch |
| `status:done` | Accepted and closed | CTO only |
| `status:blocked` | Waiting on dependency or decision | CTO only |
| `status:needs-jj` | CEO decision required | CTO only |

Sub-agents normally only need to set `status:new`. Do not set `status:done`, `status:blocked`, or `status:needs-jj` unless the CTO explicitly instructed it.

Priority labels are informational for sub-agents: `priority:high`, `priority:medium`, `priority:low`.

---

## Required Exit Steps

Every sub-agent must complete these steps before exiting:

1. Post a GitHub issue comment with:
   - what you did
   - what result you got
   - what validation you performed, if any
   - any blocker or recommended next step
2. Remove `status:in-progress` and add `status:new`.
3. Verify the label change succeeded.
4. Leave the issue open.

Required label command:

```bash
gh issue edit <NUMBER> --repo <OWNER/REPO> --remove-label "status:in-progress" --add-label "status:new"
gh issue view <NUMBER> --repo <OWNER/REPO> --json labels | jq -r '.labels[].name'
```

If `status:in-progress` is still present after the update attempt, the pass is not finished. Fix the label state before exiting.

Universal checklist:

- [ ] Work completed or failure documented
- [ ] Evidence comment posted on the GitHub issue
- [ ] Ticket returned to `status:new`
- [ ] Verified `status:in-progress` was removed
- [ ] Issue left open

---

## Dependencies

Tickets with a `### Dependencies` section listing `- [ ] #N` issue refs use GitHub's native tracked issues.

Unblocking is automatic: `framework/board-review/workflows/unblock-dependencies.yml` checks `status:blocked` tickets when dependencies close and returns unblocked tickets to `status:new`.

Sub-agents should not manually manage dependency status unless the CTO dispatch specifically asks for it.

---

## Branch And Deployment Rules

These rules apply only when the CTO assigned implementation, review, validation, or deployment work.

| Action | Who | Notes |
|--------|-----|-------|
| Work in isolated worktree | Engineer | `/tmp/wt/{repo-short}-{ticket-num}`, branch `fix/{repo-short}-{ticket-num}` |
| Review code in worktree | Reviewer if CTO requests review | `git diff origin/experiment..HEAD` inside the worktree |
| Run verification in worktree or deployed env | Validation role chosen by CTO | Match the CTO validation plan |
| Merge worktree branch -> `experiment` | Validation role chosen by CTO | Only when explicitly authorized |
| Test on experiment endpoint | Validation role chosen by CTO | Browser automation, never localhost, when deployed verification is required |
| Clean up worktree | Validation role that finishes the deployed pass | `git worktree remove /tmp/wt/{name} --force` when done |
| Close tickets | CTO only | Sub-agents never close issues |
| Merge `experiment` -> `main` | CEO (JJ) only | Production deployment |

There is no universal required implementation pipeline. Follow the CTO dispatch prompt.

---

## Engineer Implementation Handoff

This section applies to engineer implementation passes. It does not apply to code-review-only, QA-only, product-analysis, or editorial passes unless the CTO dispatch says otherwise.

Before an engineer returns a ticket to CTO, the ticket comment must explicitly include:

- confirmation the branch was synced/rebased from latest `origin/experiment`
- confirmation the fix was tested locally on `http://localhost:<port>` (any localhost port is acceptable)
- the exact feature or bugfix flow exercised locally
- the expected result actually observed in the running app
- console/runtime error status
- relevant tests that passed

Required template:

```markdown
**Engineer handoff checklist:**
- [x] Synced/rebased from latest `origin/experiment`
- [x] Tested locally on `http://localhost:8511` (or any localhost port actually used)
- [x] Verified: <exact feature / bugfix flow exercised locally>
- [x] Expected result observed: <what worked in the running app>
- [x] Tested edge case(s): <notes>
- [x] Console/runtime errors: none (or explain exactly what appeared)
- [x] Relevant tests passed: <unit / integration / e2e>
- [x] Ready for code review
```

If this handoff comment is missing, incomplete, or does not mention sync-from-`experiment`, localhost verification, the exact flow exercised, the observed result, and console/runtime error status, the next CTO pass should treat the handoff as incomplete and send it back for correction instead of advancing.

Suggested CTO rejection comment:

```markdown
Review rejected: engineer handoff incomplete.

Before code review, the engineer must post a handoff comment confirming:
- branch synced/rebased from latest `origin/experiment`
- local verification completed on `http://localhost:<port>` (any localhost port is acceptable)
- the exact feature or bugfix flow exercised locally
- the expected result actually observed in the running app
- console/runtime error status
- relevant tests passed

Resetting to `status:new` so an engineer can complete the required pre-review validation.
```

---

## PRECHECK_STATE.json - Hands Off

Only the automation precheck reads or writes `framework/board-review/PRECHECK_STATE.json`. Fix GitHub labels to unstick the pipeline.
