# Bugfix

**Purpose:** Guide CTO planning for a concrete defect with a likely implementation path.

**What this covers:**
- When to use the bugfix workflow
- Planning expectations before dispatch
- Typical implementation, review, validation, and closure path

Use when the ticket describes a concrete defect with enough evidence to choose an implementation path.

Default path:
1. CTO triage and planning
2. Engineer fix
3. Focused review
4. Targeted validation
5. CTO acceptance decision
6. Close

CTO planning should define:
- the suspected failure surface
- the narrowest acceptable fix scope
- the validation evidence required before closure
- whether production behavior is diagnostic only or an approved validation target

Notes:
- prefer narrow fixes
- validation should match the bug surface
- repeated failures still follow the global retry limit
