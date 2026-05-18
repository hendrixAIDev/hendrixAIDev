# Role Conventions - Shared Role Practice

**Purpose:** Define common working practices for role-based agents, regardless of the specific role they are assigned.

**What this covers:**
- Code navigation and dependency awareness
- Testing and verification standards
- File and documentation hygiene
- Git safety and scoped changes
- Handoff expectations and authority boundaries

**Last Updated:** 2026-05-16

---

## Core Principles

1. Understand the assignment before changing files.
2. Keep the change scoped to the assigned responsibility.
3. Prefer existing project patterns and helper tools over inventing new process.
4. Verify behavior with evidence before calling work complete.
5. Leave a clear handoff for the next person or agent.

Workflow-specific lifecycle rules belong in the workflow docs that own them, not in this shared role-practice file.

---

## Read Before You Write

Before making changes:

1. Read the dispatch prompt or assignment carefully.
2. Read the relevant code and project docs.
3. Check whether a relevant helper skill exists under skills/.
4. Read PROJECT_STRUCTURE.md and DOCUMENTATION.md when file placement or documentation changes are involved.
5. Identify the smallest verification gate that can prove the work.

Do not start by editing when you have not found the code path, owner doc, or expected behavior.

---

## Code Navigation

Use fast search first, then inspect the concrete code path.

~~~bash
rg -n "save_card" src/ --glob='*.py'
~~~

When changing functions, classes, module paths, imports, API contracts, database schema, or shared UI state, check references before editing.

If the project provides code-navigation tooling, use it for dependency checks. For this workspace, the code-nav skill documents the shared helper:

~~~bash
bash skills/code-nav/scripts/code-nav.sh refs src/core/db_storage.py 494 8
bash skills/code-nav/scripts/code-nav.sh goto src/core/db_storage.py 531 18
bash skills/code-nav/scripts/code-nav.sh names src/ --type class
~~~

Do not commit generated dependency artifacts such as DEPENDENCY_GRAPH.json; regenerate them when needed.

---

## Scope Discipline

Keep the diff focused.

- Change only files needed for the assigned task.
- Avoid opportunistic refactors.
- Do not reformat unrelated files.
- Do not revert work you did not make unless explicitly instructed.
- If unrelated local changes exist, work around them and call them out when relevant.

Before handoff, inspect the diff against the expected base branch or worktree baseline.

---

## Verification Standards

"Done" means verified, not only changed.

Use verification that matches the risk:

- Pure logic change: focused unit tests plus relevant existing tests.
- API or persistence change: integration test or direct runtime check.
- UI change: local running app check or browser verification.
- User-facing flow: exercise the actual flow, including failure or empty states when relevant.
- Documentation-only change: direct read-through and link/path checks.

When a bug is being fixed, prefer a test or reproduction that fails before the fix and passes after it. If that is not practical, document the manual reproduction and verification clearly in the handoff.

If verification is blocked, say exactly what blocked it and what remains unproven.

---

## Runtime Checks

For UI, API, or user-facing work, run the smallest meaningful runtime check before handoff.

Examples:

- Start the local app or service.
- Exercise the changed screen or endpoint.
- Check console/runtime errors.
- Confirm the expected state change or rendered output.
- Capture the command or browser path used.

Use project-specific docs for exact commands, credentials, endpoints, and deploy targets. Do not hardcode product-specific runtime details in this shared conventions file.

---

## Database Safety

Treat database access as high risk.

- Prefer the application's database layer for implementation tests.
- Use read-only queries for inspection unless explicitly authorized.
- Do not run writes against production data from a role session unless the assignment explicitly grants that authority.
- If a database tool has broad credentials, behave as though safety is enforced by convention, not by the tool.

Record the environment used for any database verification.

---

## Git Safety

Keep Git history and issue automation predictable.

Avoid commit-message keywords that auto-close GitHub issues unless the owning workflow explicitly asks for them:

- Fix #123, Fixes #123, Fixed #123
- Close #123, Closes #123, Closed #123
- Resolve #123, Resolves #123, Resolved #123

Use safer references:

- Implement auth timeout handling (ref #123)
- Add health endpoint - relates to #123
- [#123] Add timeout tests

Do not push, merge, or deploy unless the dispatch prompt or owning workflow explicitly authorizes that action.

---

## File And Documentation Hygiene

Follow PROJECT_STRUCTURE.md for file placement and DOCUMENTATION.md for documentation standards.

Quick rules:

- Temporary analysis belongs in tmp/ or should be deleted.
- Completion logs belong in daily memory when persistence is needed.
- Update existing docs before creating new ones.
- Do not create report or completion files unless the owning workflow explicitly needs them.
- Document decisions and non-obvious workflows, not every implementation detail.

Major docs should start with a short purpose and coverage description.

---

## Communication And Handoff

Handoffs should be evidence-based and concise.

Include:

- What changed
- Files changed
- Verification performed
- Results observed
- Assumptions or risks
- Blockers, if any
- Recommended next step when useful

If you made a judgment call, state the reasoning briefly. If something is unverified, say so directly.

---

## Authority Boundaries

Follow the authority granted by the dispatch prompt and the relevant owning workflow.

By default:

- Do not take external public actions.
- Do not expose private data or credentials.
- Do not run destructive commands without explicit authorization.
- Do not merge to production branches.
- Do not make legal, financial, or strategic decisions.

Workflow-specific status, closure, phase flow, and deployment gates are governed by the docs for that workflow, not this file.

---

## Related Docs

| Document | Owns |
|----------|------|
| framework/roles/cached/ | Role definitions |
| framework/roles/overlays/ | Role-specific and shared overlays |
| PROJECT_STRUCTURE.md | Workspace file placement |
| DOCUMENTATION.md | Documentation standards |
