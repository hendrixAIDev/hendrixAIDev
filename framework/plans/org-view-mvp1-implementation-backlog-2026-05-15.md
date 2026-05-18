# Org View MVP 1 Implementation Backlog

**Created:** 2026-05-15 22:10 PDT  
**Product:** Framework  
**Scope:** Read-only organization operations map MVP 1 with org-wide summary plus one ChurnPilot detail page  
**Primary source of truth for v1:** per-product board-review state files, product task queues, and GitHub issue/status-label state.

## Objective

Turn the existing organization-view proposal into a CTO-ready implementation backlog for a first release that is intentionally narrow:

- org-wide summary first
- one ChurnPilot detail page second
- all active roles visible
- read-only only
- no retry/stall analytics in v1

## Guardrails

- Treat per-product board-review state files, product task queues, and GitHub issue/status-label state as the initial backing sources for the pilot view.
- Do not use a shared fleet-status Markdown file as the backing source.
- Use the existing normalized stage framing from `framework/plans/org-view-visualization.md`.
- Keep product framing stable enough that CTO can promote tasks into execution tickets without re-writing the PM intent.
- Do not expand v1 into write actions, workflow controls, or cross-product deep-detail pages.

## Backlog

### 1. Define the MVP 1 view contract and success boundaries

- **Recommended order:** 1
- **Dependencies:** None
- **Owner / role suggestion:** Product Manager with CTO review
- **Task:** Freeze the exact MVP 1 information contract for the org summary and the ChurnPilot detail page, including what must be shown above the fold, which role chips are required, which normalized stage groups appear, and which raw state fields are intentionally hidden in v1.
- **Acceptance criteria:**
  - A written field-level contract exists for the org summary and ChurnPilot detail view.
  - The contract explicitly names the required roles: PM, CTO, Engineer, Reviewer, and QA.
  - The contract explicitly states that v1 is read-only and uses per-product state, queue, and GitHub ticket/status-label state first.
  - The contract explicitly excludes retry/stall analytics and non-ChurnPilot product detail pages.
- **Explicitly out of scope:**
  - UI implementation details such as component library choice or layout code.
  - Workflow mutation, retry controls, or agent/session transcript ingestion as required v1 dependencies.
  - Any interactive controls such as retry, wake, assign, or filter persistence.

### 2. Map product state, queue state, and GitHub ticket state into a stable product-facing view model

- **Recommended order:** 2
- **Dependencies:** Task 1
- **Owner / role suggestion:** Backend Engineer or Full-Stack Engineer
- **Task:** Define the translation layer that turns per-product board-review state files, product task queues, and GitHub issue/status-label state into the MVP 1 display model for both the org summary and the ChurnPilot pilot detail, including role-state inference and normalized work-stage grouping.
- **Acceptance criteria:**
  - Every field shown in MVP 1 has a documented source path from product state, queue state, GitHub ticket/status-label state, or a documented fallback.
  - ChurnPilot summary output can represent ticket actionability, current status text, and stage grouping without requiring new operational writes.
  - Role-chip states are derived using the shared vocabulary from the org-view proposal and do not invent extra status classes.
  - The mapping notes identify where the source is approximate or lossy so CTO understands future reconciliation work.
- **Explicitly out of scope:**
  - Deep historical reconciliation across raw run logs, session transcripts, and stale status archives.
  - Historical trend lines, retry counts, stall detection, or SLA-style timing analysis.
  - Mutating board-review artifacts to better fit the UI.

### 3. Deliver the org-wide summary surface as the default entry view

- **Recommended order:** 3
- **Dependencies:** Tasks 1-2
- **Owner / role suggestion:** Frontend Engineer
- **Task:** Implement the default organization summary view that lists all active products from the current framework scope and surfaces a scannable state summary per row: product identity, current status, actionability signal, and whether deeper detail is available for the ChurnPilot pilot page.
- **Acceptance criteria:**
  - The default page presents an org-first summary before any product detail.
  - All currently tracked products in the product-state scope are represented gracefully, even if their available detail is thin.
  - ChurnPilot is visibly identifiable as the only MVP 1 deep-dive page.
  - The summary remains legible when products have no actionable tickets or sparse state.
- **Explicitly out of scope:**
  - Deep detail pages for StatusPulse, Framework, Personal Brand, OpenClaw Assistant, or CLSE.
  - Sorting/ranking based on retry intensity, stall risk, or automation health scoring.
  - Editing actions, bulk actions, or saved custom dashboard states.

### 4. Deliver the ChurnPilot pilot detail page with full active-role visibility

- **Recommended order:** 4
- **Dependencies:** Tasks 1-3
- **Owner / role suggestion:** Frontend Engineer with PM validation
- **Task:** Build the single product detail page for ChurnPilot that expands the summary into the pilot-level read-only view: product metadata, active issue context, normalized stage summary, and visible role chips for PM, CTO, Engineer, Reviewer, and QA.
- **Acceptance criteria:**
  - ChurnPilot detail is reachable from the org summary in a straightforward way.
  - All five roles are displayed even when some roles are idle.
  - The page shows active issue context and normalized work-stage framing consistent with the org-view proposal.
  - The page stays read-only and does not imply unsupported operational precision beyond the source artifact.
- **Explicitly out of scope:**
  - Role timelines, per-agent transcripts, sub-agent drilldowns, or queue-item editing.
  - Retry/stall analytics, pass-duration analytics, or run-attempt counters.
  - Cross-product comparison widgets embedded inside the ChurnPilot detail page.

### 5. Add source-state transparency and empty/approximate-state handling

- **Recommended order:** 5
- **Dependencies:** Tasks 2-4
- **Owner / role suggestion:** Full-Stack Engineer with QA support
- **Task:** Make the MVP honest about its source quality by adding lightweight provenance, refresh context, and empty-state behavior so JJ/CTO can trust what the pilot is and is not claiming.
- **Acceptance criteria:**
  - The UI identifies product state, queue state, and GitHub ticket/status-label state as the initial backing sources for the pilot.
  - Last-refresh or source-timing context is visible wherever stale interpretation would otherwise be misleading.
  - Empty/sparse product states render as intentional states rather than broken UI.
  - Approximate or inferred role/stage states are presented clearly enough that users can distinguish cached/local source data from authoritative live orchestration state.
- **Explicitly out of scope:**
  - Auto-refresh orchestration, live polling, or real-time subscriptions.
  - Audit logs, historical playback, or trust-scoring dashboards.
  - Data quality repair workflows that rewrite the source artifact.

### 6. Verify MVP 1 against the locked product contract before CTO promotion

- **Recommended order:** 6
- **Dependencies:** Tasks 1-5
- **Owner / role suggestion:** QA with CTO sign-off
- **Task:** Run a read-only product verification pass that checks scope discipline, role visibility, source-of-truth alignment, and graceful handling of sparse fleet states before the implementation is considered ready for broader rollout or follow-on tickets.
- **Acceptance criteria:**
  - Verification confirms the default landing view is the org summary and the only deep detail page is ChurnPilot.
  - Verification confirms all active roles are visible on the ChurnPilot page.
  - Verification confirms the implementation remains read-only and excludes retry/stall analytics.
  - Verification documents any mismatch between the UI wording and the fidelity of the product state, queue state, and GitHub ticket/status-label inputs.
- **Explicitly out of scope:**
  - Expanding the pilot to more products during QA.
  - Defining v2 reconciliation architecture during the verification pass.
  - Performance or scale work beyond what is needed to confirm the MVP behaves correctly.

## Recommended execution sequence

1. Lock the MVP 1 contract.
2. Define the product-state/queue/ticket-to-view-model mapping.
3. Build the org-wide summary surface.
4. Build the ChurnPilot detail page.
5. Add source transparency and sparse-state handling.
6. Run the scoped QA/CTO verification gate.

## Dependencies summary

- Task 1 is the scope lock and should happen first.
- Task 2 depends on Task 1 because the mapping should serve the locked MVP contract, not an expanding UI.
- Tasks 3 and 4 depend on Task 2 so the summary and pilot page share one vocabulary and do not drift.
- Task 5 depends on the earlier surfaces so transparency and empty states are implemented against the real UI shape.
- Task 6 depends on the full slice being present and is the handoff gate for CTO promotion.

## Explicit v1 exclusions

- Retry analytics
- Stall analytics
- Live multi-source reconciliation
- Product detail pages beyond ChurnPilot
- Workflow mutation controls
- Agent/session transcript drilldowns
- Historical reporting or trend analysis

## CTO handoff note

This backlog is intentionally framed so each numbered item can be promoted into a future execution ticket without changing the product intent: JJ-first summary view, one ChurnPilot pilot detail, all active roles visible, read-only interactions, and per-product state plus queue and GitHub ticket/status-label state as the first-state inputs for MVP 1.
