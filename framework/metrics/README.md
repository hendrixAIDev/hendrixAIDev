# Pipeline Quality Metrics

**Purpose:** Score every stage of the board review pipeline to enable data-driven optimization (and eventually DSPy compilation).

**Location:** `framework/metrics/` — pipeline infrastructure, spans all projects.

## Data Files

| File | Stage | Who writes | When |
|------|-------|-----------|------|
| `review-quality.jsonl` | Code Review | CTO (Phase 4, on ticket closure) | Ongoing |
| `engineer-quality.jsonl` | Engineering | CTO (Phase 4, on ticket closure) | Planned |
| `qa-quality.jsonl` | QA Verification | CTO (Phase 4, on ticket closure) | Planned |
| `triage-quality.jsonl` | CTO Triage | Darwin Loop (weekly retro) | Planned |

## How Labels Are Generated

**Ongoing (automatic):** When the CTO closes a ticket in Phase 4, it scores the preceding stages by examining:
- Number of review/dispatch rounds (from GitHub comments)
- Whether QA passed on first try
- Whether labels were updated correctly
- Whether scope was respected

**Bootstrap (one-off):** Retroactively label closed tickets from GitHub comment history.

## Quality Tiers

- `good` — Passed next stage on first try, no rework needed
- `acceptable` — Minor issues caught, 1 rework round
- `poor` — Multiple rework rounds, missed critical issues
- `failed` — Approved code that broke in production, or rejected code that was correct

## Field Definitions

See `schemas/metrics-schema.md` for detailed field specs per stage.

## Usage

- **Darwin Loop:** Reads metrics weekly to identify systemic issues
- **DSPy (future):** Training data for prompt optimization
- **Manual review:** JJ/CTO can audit pipeline health
