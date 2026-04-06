# Pipeline Quality Metrics

**Purpose:** Score every stage of the board review pipeline to enable data-driven optimization (and eventually DSPy compilation).

**Location:** `framework/metrics/` — pipeline infrastructure, spans all projects.

## Data Files

| File | Stage | Who writes | When |
|------|-------|-----------|------|
| `review-quality.jsonl` | Code Review | CTO (Phase 4, on ticket closure) | ✅ Active (48 records) |
| `engineer-quality.jsonl` | Engineering | CTO (Phase 4, on ticket closure) | ✅ Active |
| `qa-quality.jsonl` | QA Verification | CTO (Phase 4, on ticket closure) | ✅ Active |
| `triage-quality.jsonl` | CTO Triage | CTO (Phase 4, on ticket closure) | ✅ Active |

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

## Shared Knowledge

| File | Purpose |
|------|---------|
| `framework/knowledge/streamlit-gotchas.md` | Compiled Streamlit pitfalls from EvoMap capsules. Referenced by fullstack + frontend overlays. |

## Usage

- **CTO Board Review:** Writes all 4 JSONL files during Phase 4 (ticket closure)
- **DSPy Shadow Mode:** Training data for prompt optimization (50+ examples per stage enables compilation)
- **Manual review:** JJ/CTO can audit pipeline health
- **Trend analysis:** Score averages over time show whether prompt changes improve quality
