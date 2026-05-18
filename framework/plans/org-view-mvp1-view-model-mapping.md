# Org View MVP 1 View Model Mapping

**Created:** 2026-05-15 23:02 PDT  
**Product:** Framework  
**Scope:** Translation layer from per-product board-review state files, product task queues, and GitHub issue/status-label state into the MVP 1 Organization Operations Map view contract  
**Primary contract source:** `framework/plans/org-view-mvp1-view-contract.md`

## Purpose

Define how per-product board-review state files, product task queues, and GitHub issue/status-label state map into the read-only MVP 1 org summary and ChurnPilot detail view model.

This artifact is intentionally conservative. When the source does not provide enough evidence, the mapping must:

- use the normalized product vocabulary from the view contract
- fall back to intentional idle or empty states
- mark sparse, stale, inferred, and approximate fields explicitly
- avoid inventing ticket-level or role-level precision that the available state does not support

## v1 source boundary

MVP 1 reads from these initial backing sources:

- `framework/board-review/state/*.md` for product identity, owned repository list, durable CTO handoff notes, active dispatch pointers, and recent product-level result text
- product task queues, including `framework/plans/task_queue/tasks.yaml` and `projects/churn_copilot/plans/task-queue.yaml`, for PM backlog, dependencies, queue state, and blocked/proposed work
- GitHub issue/status-label state, either fetched live or read from a documented precheck cache, for authoritative ticket actionability and workflow stage
- `framework/board-review/PRECHECK_STATE.json` only as runtime/cache context when it records the latest scan result used by the board-review precheck

A shared fleet-status Markdown file is not a backing source for MVP 1. It must not decide ticket actionability, active-work counts, role state, or product continuity.

This means the mapper has enough structured sources for multiple simultaneous tickets, but it is still not authoritative for:

- live agent transcript content
- exact role ownership beyond ticket/dispatch/queue evidence
- active run/session truth unless a future source explicitly adds runlock ingestion
- retry/stall analytics

## Source shape assumed by the mapper

The mapper consumes these fields when present:

- product state: `product`, `slug`, `sessionKey`, `repos`, `taskQueue`, `lastRunAt`, `lastResult`, `currentBlockers`, `activeDispatches`, and `handoffNotes`
- task queue: `id`, `title`, `priority`, `status`, `github_issue`, `evidence`, `pm_notes`, `cto_notes`, and dependency/blocking notes
- GitHub issue state: number, title, state, labels, body summary, and latest relevant handoff/comment when available
- precheck cache: latest scan timestamp and actionable issue list when used instead of a live GitHub query

From each product state file, the mapper uses:

- product identity and repo ownership
- the linked task queue path
- active dispatches and latest durable handoff/result text
- current blockers and cross-run handoff notes

## Translation principles

1. Product-facing vocabulary must use normalized stage groups, not raw board-review wording, as the primary label.
2. Current status text should prefer current ticket/queue state, then product state `lastResult`, then a conservative empty-state fallback.
3. Empty or inactive products should render as intentional idle states, not as missing data.
4. ChurnPilot detail should show the full field contract even when some operational detail is unavailable from the structured sources.
5. Any field derived from cached GitHub state, prose handoff notes, or queue notes rather than explicit current labels must be marked inferred or approximate.

## Product identity mapping

Use these stable product keys in the MVP 1 mapper:

| Product state file | product_key | product_name | detail_page_available |
|---|---|---|---|
| `framework/board-review/state/churnpilot.md` | `churnpilot` | `ChurnPilot` | `true` |
| `framework/board-review/state/statuspulse.md` | `statuspulse` | `StatusPulse` | `false` |
| `framework/board-review/state/framework.md` | `framework` | `Framework` | `false` |
| `framework/board-review/state/personal-brand.md` | `personal-brand` | `Personal Brand` | `false` |
| `framework/board-review/state/openclaw-assistant.md` | `openclaw-assistant` | `OpenClaw Assistant` | `false` |
| `framework/board-review/state/clse.md` | `clse` | `CLSE` | `false` |

Fallback:

- If a new product state file appears and no explicit key mapping exists, derive `product_key` from its `slug` or by lowercasing the product name and slugging spaces to hyphens.
- Preserve the original product label as `product_name`.
- Set `detail_page_available=false` unless the product is exactly ChurnPilot in MVP 1.

## Normalized stage-group inference

MVP 1 infers stage groups from the best available structured evidence, with GitHub `status:*` labels first, task queue status second, active dispatch/product state third, and prose handoff notes last.

### Priority order

1. Explicit GitHub `status:blocked`, queue `blocked`, or product-state blocker
2. Explicit GitHub `status:needs-jj`, `status:cto-review`, or queue `needs_human`
3. Explicit GitHub `status:review` or `status:verification`
4. Explicit GitHub `status:in-progress`, queue `in_progress`, or active dispatch
5. Explicit GitHub `status:new`, queue `ticketed`, `triaged`, or actionable precheck entry
6. Queue `proposed` discovery work
7. No open actionable GitHub issue and no non-done queue work
8. Sparse fallback

### Inference rules

| Source evidence | normalized_stage_group | Notes |
|---|---|---|
| GitHub `status:blocked`, queue `blocked`, or current blocker exists | `Blocked` | Strongest product-facing signal. |
| GitHub `status:needs-jj`, `status:cto-review`, or queue `needs_human` | `Awaiting final decision` | Authoritative when from GitHub/queue, approximate from prose notes. |
| GitHub `status:review` | `In review` | Use raw label only as supporting context. |
| GitHub `status:verification` | `In verification` | Use raw label only as supporting context. |
| GitHub `status:in-progress`, queue `in_progress`, or active dispatch | `In execution` | Prefer issue label over active dispatch if they conflict. |
| GitHub `status:new`, queue `ticketed`/ `triaged`, or precheck actionable issue | `Ready for CTO` | Work is ready for CTO triage or next dispatch. |
| Queue `proposed` without a ticket | `Discovery` | PM/backlog discovery; not execution-ready yet. |
| No open actionable GitHub issue and all known queue items are done/rejected | `Done` | Means no currently actionable open work, not product complete forever. |
| No clear stage evidence | `Discovery` | Attach a sparse source note. |

### Stage summary text rules

The detail view should generate `stage_summary_text` using a short explanation tied to the inferred stage:

- `Blocked`: “Current state says active work is blocked.”
- `Ready for CTO`: “Current ticket or queue state indicates actionable work that likely needs CTO triage or the next dispatch.”
- `In execution`: “Current ticket, queue, or dispatch state implies execution work is in flight.”
- `In review`: “Current ticket or dispatch state implies work is awaiting or undergoing review.”
- `In verification`: “Current ticket or dispatch state implies work is awaiting or undergoing verification.”
- `Awaiting final decision`: “Current ticket or queue state implies CTO or JJ decision is the next gating step.”
- `Done`: “Current ticket and queue state report no open actionable work.”
- `Discovery`: “Current state does not expose a stronger structured workflow signal.”

## Org-wide summary field mapping

| Contract field | Source | Fallback / approximation behavior | Fidelity note |
|---|---|---|---|
| `product_key` | Product state `slug` or identity mapping table | Slug product name if unmapped | Derived stable key |
| `product_name` | Product state `product` | Use mapped name from state file path | Direct when present |
| `repo` | Product state `repos` | `Unknown repo` if missing | Direct when present |
| `current_status_text` | Active GitHub issue summary, queue state, product state `lastResult` | “No current status text available from product state or tickets.” | Prefer structured state over prose notes |
| `normalized_stage_group` | GitHub status label, queue status, active dispatch, blocker, then handoff text | `Discovery` | Authoritative when label/queue-backed; inferred when prose-backed |
| `actionability_signal` | GitHub actionable issue state and queue blockers | Use `action needed`, `blocked`, `idle`, or `unknown` as coarse values | Coarse product-facing summary |
| `next_attention_text` | Derived from active issue/queue status and inferred stage | If no clearer signal: “No immediate actionable work is visible in current product state.” | May be inferred from queue/ticket state |
| `open_actionable_ticket_count` | GitHub open issues with actionable `status:*` labels or precheck actionable issue cache | Otherwise `null` or display as approximate unknown, not fabricated | Prefer live GitHub; mark cached counts |
| `active_issue_titles` | GitHub issue titles for active/actionable issues | Empty list when unavailable | Direct when present |
| `detail_page_available` | Identity mapping rule | `false` for all products except ChurnPilot | Product-policy field, not source data |
| `source_confidence_note` | Derived from source quality checks across state, queue, and GitHub/cache | Summarize stale/sparse/inferred/approximate conditions per row | Required honesty field |

### Actionability signal vocabulary

Use a compact v1 vocabulary:

- `action needed` — actionable work likely exists now
- `blocked` — blocker is the dominant signal
- `idle` — no open actionable work visible
- `unknown` — available state is too sparse to classify confidently

### Next-attention text heuristics

| Inferred stage | next_attention_text |
|---|---|
| `Ready for CTO` | “CTO should review the product’s next actionable work.” |
| `In execution` | “Execution is in flight; next attention is the result of the active pass.” |
| `In review` | “Review outcome is the next gating step.” |
| `In verification` | “Verification outcome is the next gating step.” |
| `Awaiting final decision` | “Final decision is the next gating step.” |
| `Blocked` | “Resolve the blocker before work can advance.” |
| `Done` | “No immediate action is visible from current product and ticket state.” |
| `Discovery` | “Snapshot is too thin to name the next step confidently.” |

## ChurnPilot detail field mapping

The ChurnPilot pilot page uses the ChurnPilot product state file, ChurnPilot task queue, and ChurnPilot GitHub issue/status-label state, then expands it with explicit transparency about missing detail.

### Required product context fields

| Contract field | Source | Fallback / approximation behavior | Fidelity note |
|---|---|---|---|
| `product_key` | `framework/board-review/state/churnpilot.md` routing table | `churnpilot` | Derived stable key |
| `product_name` | `framework/board-review/state/churnpilot.md` routing table | `ChurnPilot` | Direct |
| `repo` | `framework/board-review/state/churnpilot.md` routing table | `hendrixAIDev/churn_copilot_hendrix` if state is missing the repo | Direct when present |
| `detail_scope_label` | Product policy | “MVP 1 pilot detail page” | Not source data |
| `snapshot_source` | Source identity list | `framework/board-review/state/churnpilot.md`, `projects/churn_copilot/plans/task-queue.yaml`, and GitHub issue/status-label state | Constant provenance field |
| `snapshot_timestamp_text` | Product state `lastRunAt`, queue `updated_at`, and GitHub/precheck fetch timestamp when available | “Source timing unavailable.” | Direct metadata when present |
| `source_fidelity_note` | Derived from source caveats + sparsity | “Backed by product state, queue state, and ticket labels; role-level detail may still be inferred when no active dispatch is present.” | Required honesty field |

### Required active work fields

| Contract field | Source | Fallback / approximation behavior | Fidelity note |
|---|---|---|---|
| `active_issue_count` | GitHub active/actionable issues for the ChurnPilot repo, or documented precheck cache | `0` only when live/cache state has no actionable open issues; otherwise unknown/approximate | Mark cached counts |
| `active_issue_titles` | GitHub issue titles for active/actionable ChurnPilot issues | Empty list | Direct when available |
| `active_issue_numbers` | GitHub issue numbers | Empty list | Optional when unavailable |
| `current_status_text` | Active issue summary, queue state, product state `lastResult` | “No current status text available from ChurnPilot state or tickets.” | Prefer structured state over prose |
| `normalized_stage_group` | GitHub status label, queue status, active dispatch, blocker, then handoff text | `Discovery` | Authoritative when label/queue-backed; inferred when prose-backed |
| `stage_summary_text` | Derived from stage + source evidence | Use generic stage summary rules | May be inferred |
| `next_attention_text` | Derived from stage + source evidence | Use generic next-attention rules | May be inferred |
| `open_actionable_ticket_count` | Same logic as org summary field | `0` only for known-empty live/cache ticket state; otherwise unknown/approximate | Prefer live GitHub; mark cached counts |

### Required role-chip fields

Role chips are inferred from active dispatches, GitHub issue/status labels, task queue status, and product-state handoff notes. All five required roles must always render, even if that means showing an idle state with a source note.

| Contract field | Source | Fallback / approximation behavior | Fidelity note |
|---|---|---|---|
| `role_name` | Product-contract constant per required role chip | Always emit PM, CTO, Engineer, Reviewer, and QA in that order | Product contract field, not source data |
| `role_state` | Active dispatch role, GitHub label/stage, queue status, then product-state notes | Use role-specific idle fallback when no stronger evidence exists | Direct when dispatch-backed; inferred otherwise |
| `role_state_reason` | Generated from source evidence and inference template | Use conservative explanation that names missing evidence when sparse | Explanatory field |
| `role_source_note` | Derived from source caveats when role state is inferred indirectly or cached | Include whenever the role state is not directly supported by active dispatch or explicit ticket state | Required for inferred/cached states |

#### Role-state vocabulary for MVP 1

Use the proposal vocabulary without expanding it:

- PM: `idle`, `backlog`, `ready`, `holding`
- CTO: `idle`, `triaging`, `coordinating`, `blocked`, `needs_jj`
- Engineer: `idle`, `queued`, `active`, `returned`, `blocked`
- Reviewer: `idle`, `queued`, `active`, `returned`, `blocked`
- QA: `idle`, `queued`, `active`, `returned`, `blocked`

#### Role inference rules

| Role | Primary inference | Idle / sparse fallback | role_source_note guidance |
|---|---|---|---|
| PM | `backlog` for proposed/triaged queue work; `ready` when queue/ticket is ready for CTO; `holding` when status implies JJ/final decision; otherwise `idle` | `idle` | “PM state derived from queue and ticket state; inferred when only handoff text is available.” |
| CTO | `triaging` for `Ready for CTO`; `coordinating` for `In execution`, `In review`, or `In verification`; `blocked` for `Blocked`; `needs_jj` for `Awaiting final decision`; `idle` for `Done` or sparse inactive states | `idle` | “CTO state derived from ticket/queue stage, not live session transcript state.” |
| Engineer | `active` for active engineering dispatch or `In execution`; `blocked` for `Blocked`; `returned` for downstream review/verification; `queued` when the next dispatch is engineering; otherwise `idle` | `idle` | “Engineer state is direct only when an active dispatch names engineering.” |
| Reviewer | `queued` or `active` when ticket/dispatch references review; `blocked` for `Blocked`; `returned` when review evidently completed and work moved onward; otherwise `idle` | `idle` | “Reviewer state is direct only when issue/dispatch state names review.” |
| QA | `queued` or `active` when ticket/dispatch references verification/QA; `blocked` for `Blocked`; `returned` when verification evidently completed and work moved onward; otherwise `idle` | `idle` | “QA state is direct only when issue/dispatch state names verification or QA.” |

#### Role-state reason templates

| Role state | role_state_reason |
|---|---|
| `idle` | “No direct evidence of active work for this role appears in the current state sources.” |
| `backlog` | “Snapshot wording suggests pending discovery work but not an execution pass.” |
| `ready` | “Snapshot suggests actionable work is ready for CTO intake.” |
| `holding` | “Snapshot suggests work is waiting on a CTO or JJ decision.” |
| `triaging` | “Actionable work appears present, so CTO attention is likely needed next.” |
| `coordinating` | “The current stage implies work is already moving through execution or downstream gates.” |
| `queued` | “Role participation is implied as the next step, but active ownership is not proven by current state.” |
| `active` | “Snapshot wording implies this role’s stage is currently active.” |
| `returned` | “Current ticket or dispatch state implies this role’s pass has already handed work onward.” |
| `blocked` | “A blocker dominates the visible workflow state.” |
| `needs_jj` | “The next visible gating step appears to require JJ or final decision input.” |

### Required stage-group presentation fields

| Contract field | Source | Fallback / approximation behavior | Fidelity note |
|---|---|---|---|
| `normalized_stage_group` | GitHub status label, queue status, active dispatch, blocker, then handoff text | `Discovery` | Authoritative when label/queue-backed; inferred when prose-backed |
| `normalized_stage_legend` | Constant legend from the view contract | Always include all eight groups in shared product vocabulary | Product contract field |
| `raw_status_context` | GitHub labels, queue status, product state `lastResult`, and source timestamps | Omit if no source text exists | Supporting transparency field |

## Source confidence and fidelity notes

Generate per-product `source_confidence_note` and ChurnPilot `source_fidelity_note` from these conditions:

| Condition | Trigger | Recommended note fragment |
|---|---|---|
| Sparse | Product row exists but `Current status` is blank or generic | “Snapshot row is present but sparse.” |
| Inferred | Any normalized stage or role state derived from prose | “Stage and role states are inferred from product-level status text.” |
| Approximate | Ticket counts or issue lists are partially inferred | “Ticket counts and active issue detail are approximate or unavailable.” |
| Stale | Product state `lastRunAt`, queue `updated_at`, GitHub/precheck fetch timestamp, or active-dispatch timestamp is older than the UI freshness threshold | “Source state may be stale relative to live board-review and GitHub state.” |
| Lossy | Detail view asks for fields not present in the current source set | “The current sources do not contain authoritative role-level or run-state detail for this field.” |

Suggested freshness threshold for v1 UI copy:

- treat the view as potentially stale once the newest relevant source timestamp is more than 24 hours old
- if live GitHub state is unavailable but a precheck timestamp exists, use the precheck timestamp and mark ticket data as cached
- if product state, queue, and GitHub/precheck timestamps are all missing, render a high-visibility stale/unknown source note

## Fallback behavior matrix

| Scenario | Mapper behavior |
|---|---|
| Product state file missing entirely | Do not fabricate a product card unless a configured product registry exists. |
| Repo missing | Show `Unknown repo` and add a source-confidence note. |
| Status text missing | Use active issue/queue summary if available; otherwise map stage to `Discovery`, set actionability to `unknown`, and mark sparse. |
| No actionable GitHub issues and all known queue items are done/rejected | Permit zero counts, `Done` stage, idle role fallbacks, and “no immediate action” attention text. |
| GitHub/queue/product state names a blocker | Map to `Blocked`, set actionability to `blocked`, and bias CTO/Engineer role states to blocked. |
| GitHub/queue state is actionable but count is cached/unstated | Use `action needed`, map stage to `Ready for CTO`, leave ticket count unknown/approximate, and avoid inventing issue titles. |
| Source references issue number without title | Capture issue number if desired, leave title list empty, and mark issue detail as partial. |
| Source timestamps are old | Keep content read-only, but add stale note rather than suppressing data. |

## ChurnPilot example using current backing sources

Current source evidence:

- `framework/board-review/state/churnpilot.md` identifies ChurnPilot, its CTO session, repo, task queue, latest result, blockers, and active dispatches.
- `projects/churn_copilot/plans/task-queue.yaml` identifies ChurnPilot PM/backlog state.
- GitHub issue/status-label state or the latest precheck cache identifies open actionable ChurnPilot tickets.

Resulting MVP 1 output should look roughly like:

- `product_key`: `churnpilot`
- `product_name`: `ChurnPilot`
- `repo`: `hendrixAIDev/churn_copilot_hendrix`
- `current_status_text`: “No open actionable tickets in latest ticket/precheck state.”
- `normalized_stage_group`: `Done`
- `stage_summary_text`: “Current ticket and queue state report no open actionable work.”
- `actionability_signal`: `idle`
- `next_attention_text`: “No immediate action is visible from current product and ticket state.”
- `open_actionable_ticket_count`: `0`
- `active_issue_count`: `0`
- `active_issue_titles`: `[]`
- role chips:
  - PM: `idle`
  - CTO: `idle`
  - Engineer: `idle`
  - Reviewer: `idle`
  - QA: `idle`

Required note:

- “This is an idle reading from the current product, queue, and ticket sources; cached ticket state should be marked if live GitHub was not queried.”

## Explicit source limits

For MVP 1, the mapper must explicitly treat these as unavailable or non-authoritative unless a future source adds them:

- actual CTO runlock/session activity
- whether an engineer, reviewer, or QA pass is active right now
- retry/stall analytics
- per-product detail beyond the coarse status sentence

A shared fleet-status Markdown file must not be used to recover fields that are unavailable from product state, queue state, GitHub issue/status-label state, or the documented precheck cache.

This is acceptable for MVP 1 because the contract intentionally prefers a stable, honest, read-only pilot over deeper runlog/session reconciliation.

## Implementation handoff note

This mapping artifact is sufficient for the next CTO cycle to promote org-summary UI work because it defines:

- a stable product identity layer
- a normalized stage inference system
- required field behavior for sparse and empty states
- conservative role-chip inference for PM, CTO, Engineer, Reviewer, and QA
- explicit honesty rules where the backing sources are stale, cached, sparse, or lossy

The next implementation ticket should use this document as the semantic contract for the view-model adapter, not invent new source semantics inside the UI layer.
