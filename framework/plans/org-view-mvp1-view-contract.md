# Org View MVP 1 View Contract

**Created:** 2026-05-15 22:49 PDT  
**Product:** Framework  
**Scope:** Read-only Organization Operations Map MVP 1 for org-wide summary plus one ChurnPilot pilot detail page  
**Initial v1 source assumption:** per-product board-review state files, product task queues, and GitHub issue/status-label state.

## Purpose

Freeze the MVP 1 information contract so the next CTO cycle can promote data-mapping and implementation work without re-writing the product framing.

This contract defines:

- what information must appear in the org-wide summary
- what information must appear in the ChurnPilot detail page
- which roles must always remain visible
- which normalized stage groups must be used
- what belongs above the fold in MVP 1
- what is intentionally excluded from v1

This contract does **not** choose UI components, visual layout implementation, or front-end architecture.

## MVP 1 framing

- MVP 1 is **read-only**.
- MVP 1 uses per-product board-review state files, product task queues, and GitHub issue/status-label state as the **initial v1 backing sources**.
- MVP 1 does **not** use a shared fleet-status Markdown file as backing state.
- MVP 1 defaults to an **org-wide summary first** view.
- MVP 1 supports exactly **one product detail page**: ChurnPilot.
- MVP 1 must be honest about source fidelity when data is sparse, inferred, or approximate.

## Required visible roles

The ChurnPilot detail page must always show role chips for:

- PM
- CTO
- Engineer
- Reviewer
- QA

These role chips are required even when a role is idle, absent from the latest active pass, or inferred indirectly from product state, queue state, or ticket state.

## Normalized stage groups

MVP 1 must use the normalized stage groups from the org-view proposal rather than exposing raw workflow labels as the primary vocabulary.

1. **Discovery**
2. **Ready for CTO**
3. **In execution**
4. **In review**
5. **In verification**
6. **Awaiting final decision**
7. **Blocked**
8. **Done**

### Raw-state mapping guidance

- Queue states such as `proposed` and `triaged` map into **Discovery**.
- `status:new` maps into **Ready for CTO**.
- Queue states such as `ticketed` and `in_progress`, plus `status:in-progress`, map into **In execution**.
- `status:review` maps into **In review**.
- `status:verification` maps into **In verification**.
- `status:cto-review`, `status:needs-jj`, and queue `needs_human` map into **Awaiting final decision**.
- Queue `blocked` and `status:blocked` map into **Blocked**.
- Queue `done` and `status:done` map into **Done**.

MVP 1 may retain raw labels as supporting context, but the primary product-facing framing must use the normalized groups above.

## Above-the-fold boundary

### Org-wide summary above the fold

The default landing surface must show, above the fold:

- organization summary header that makes clear this is an org-wide operations snapshot
- one summary row or card per tracked product in current framework scope
- each product's current normalized stage group
- each product's current actionability signal or next-attention state
- whether deeper detail exists for that product in MVP 1

The org-wide summary must appear before any product detail.

### ChurnPilot detail above the fold

The ChurnPilot detail page must show, above the fold:

- product identity and pilot-page context
- current active issue context
- normalized stage summary
- visible role chips for PM, CTO, Engineer, Reviewer, and QA
- source-state transparency indicating the view is initially backed by product state, queue state, and GitHub ticket/status-label state

Anything below this line is supporting detail, not required for the first screenful contract.

## Org-wide summary field contract

The org-wide summary is the default entry view and must support all tracked products, even if their detail is sparse.

### Required fields per product summary item

| Field | Required | Meaning / notes |
|---|---|---|
| `product_key` | Yes | Stable product identifier used by the Framework product model. |
| `product_name` | Yes | Human-readable product name shown in the org view. |
| `repo` | Yes | Repository identity as represented in Framework sources. |
| `current_status_text` | Yes | Best available current status summary from product state, queue state, or ticket state. |
| `normalized_stage_group` | Yes | One of the eight normalized stage groups defined in this contract. |
| `actionability_signal` | Yes | Best product-facing summary of whether attention or action is needed now. |
| `next_attention_text` | Yes | Short explanation of the next decision, blocker, or follow-up. |
| `open_actionable_ticket_count` | Yes | Count of actionable open issues from GitHub issue/status-label state when available; if approximate or cached, mark as approximate. |
| `active_issue_titles` | No | Short list of currently active issue titles when available from GitHub issue state or a documented cache. |
| `detail_page_available` | Yes | Boolean that indicates whether MVP 1 supports a deep-dive page for this product. |
| `source_confidence_note` | Yes | Short note when source state is sparse, inferred, stale, cached, or approximate. |

### Org summary product-level requirements

- All products present in the current Framework product-state scope must render gracefully.
- ChurnPilot must be explicitly identifiable as the **only** product with a detail page in MVP 1.
- Products without active actionable tickets must still render an intentional summary state.
- Products with sparse source data must not appear broken or falsely precise.

## ChurnPilot detail page field contract

The ChurnPilot page is the only deep-dive detail page in MVP 1 and expands the org summary into a read-only pilot view.

### Required product context fields

| Field | Required | Meaning / notes |
|---|---|---|
| `product_key` | Yes | Stable product identifier for ChurnPilot. |
| `product_name` | Yes | Human-readable product name. |
| `repo` | Yes | Repository identity for ChurnPilot. |
| `detail_scope_label` | Yes | Explicit label that this is the MVP 1 pilot detail page. |
| `snapshot_source` | Yes | Must identify product state, queue state, and GitHub ticket/status-label state as the initial backing sources. |
| `snapshot_timestamp_text` | Yes | Best available source refresh timing context. |
| `source_fidelity_note` | Yes | Clarifies when fields are inferred, approximate, or limited by the source artifact. |

### Required active work fields

| Field | Required | Meaning / notes |
|---|---|---|
| `active_issue_count` | Yes | Count of current actionable or active issues represented in GitHub issue state or a documented cache. |
| `active_issue_titles` | Yes | Human-readable list of active issue titles when present. |
| `active_issue_numbers` | No | Issue identifiers when derivable from the source. |
| `current_status_text` | Yes | Best product-level current status summary. |
| `normalized_stage_group` | Yes | Primary current grouped stage for the product. |
| `stage_summary_text` | Yes | Short explanation of why the product is in the current normalized stage. |
| `next_attention_text` | Yes | Clear summary of what needs attention next. |
| `open_actionable_ticket_count` | Yes | Read-only actionable ticket count if derivable from GitHub issue/status-label state or a documented cache. |

### Required role-chip fields

Each required role must be shown using the same contract shape:

| Field | Required | Meaning / notes |
|---|---|---|
| `role_name` | Yes | One of PM, CTO, Engineer, Reviewer, QA. |
| `role_state` | Yes | Current visible state using the shared role vocabulary or its MVP 1 subset. |
| `role_state_reason` | Yes | Short explanation of why the role is in that state. |
| `role_source_note` | No | Optional note when the role state is inferred indirectly from product, queue, or ticket evidence. |

### Required role coverage rules

- PM, CTO, Engineer, Reviewer, and QA must all be present.
- Missing activity for a role should produce an idle or equivalent visible state, not omission.
- Role state language must remain scannable and consistent with the org-view proposal.
- MVP 1 may infer role states from ticket and board-review context, but it must not overclaim unsupported precision.

### Required stage-group presentation fields

| Field | Required | Meaning / notes |
|---|---|---|
| `normalized_stage_group` | Yes | Current grouped stage for ChurnPilot. |
| `normalized_stage_legend` | Yes | Visible legend or equivalent explanation of the normalized stage vocabulary. |
| `raw_status_context` | No | Supporting raw labels or notes when useful for transparency. |

## Source assumptions for v1

MVP 1 assumes these sources are sufficient as the initial view-model inputs:

- per-product board-review state files in `framework/board-review/state/*.md` for product identity, durable CTO handoff notes, active dispatch pointers, and recent product-level result text
- product task queues such as `framework/plans/task_queue/tasks.yaml` and `projects/churn_copilot/plans/task-queue.yaml` for PM backlog, dependencies, queue status, and blocked/proposed work
- GitHub issue/status-label state, either fetched live or read from a documented precheck cache, for authoritative ticket actionability and workflow stage
- source transparency that distinguishes live GitHub truth, local queue/state artifacts, and cached or approximate values

The v1 contract does **not** use a shared fleet-status Markdown file as product backing state. Product state, queue state, and GitHub issue/status-label state are the backing sources for ticket actionability, role state, and active-work counts.

The v1 contract does **not** require direct ingestion from raw run logs, session transcripts, archived fleet snapshots, or workflow-control surfaces.

## v1 exclusions

The following are explicitly out of scope for MVP 1:

- retry analytics
- stall analytics
- non-ChurnPilot product detail pages
- workflow mutation controls
- UI implementation decisions
- component library choices
- layout code or page implementation
- live multi-source reconciliation requirements
- historical trend analysis
- agent or session transcript drilldowns

### Workflow mutation controls excluded from v1

Examples of excluded controls include:

- retry
- wake
- assign
- advance stage
- edit queue state
- persistent filters or saved dashboard controls

MVP 1 is a read-only operations view, not a workflow control surface.

## Success boundary for downstream CTO promotion

This contract is complete enough when:

- a mapping ticket can trace every required org-summary field and ChurnPilot-detail field to an initial source or documented approximation
- engineering can build the org summary and ChurnPilot pilot page without re-opening product scope
- QA can verify read-only scope, role visibility, stage grouping, and source transparency against one stable PM artifact

If later work needs new fields outside this contract, that is a v2 or follow-on scope discussion rather than silent MVP 1 expansion.
