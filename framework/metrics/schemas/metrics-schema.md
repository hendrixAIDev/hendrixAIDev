# Metrics Schema Definitions

## review-quality.jsonl

Each line is a JSON object with these fields:

```json
{
  "ts": "ISO-8601 timestamp of ticket closure",
  "trace_id": "REPO#TICKET — e.g. churn_copilot_hendrix#99 — links review → QA → engineer records",
  "commit_hash": "HEAD commit SHA of the reviewed branch (short form ok)",
  "repo": "owner/repo",
  "ticket": "#N",
  "ticket_title": "Short title",
  "reviewer_session": "cron job name or session id",
  "review_rounds": 1,
  "verdict": "APPROVE|REJECT|REQUEST_CHANGES",
  "lint_gate_enforced": true,
  "scope_violation_flagged": false,
  "findings_count": 3,
  "actionable_findings": 2,
  "qa_passed_first_try": true,
  "false_rejection": false,
  "label": "good|acceptable|poor|failed|unknown",
  "calculated_score": 0.87,
  "notes": "Optional context"
}
```

### `trace_id` — Global Linker

Format: `{repo_short}#{ticket_number}` — e.g. `churn_copilot_hendrix#99`

*Purpose:* Cross-links entries across all JSONL files. A single ticket generates up to 4 records (review, engineer, qa, triage) — all share the same `trace_id`. Enables joining downstream results (QA outcome) back to the review that preceded them.

### `calculated_score` — DSPy Reward Signal

A `0.0–1.0` float computed from raw fields using this formula:

```python
def calculate_score(entry: dict) -> float:
    # Base from human label
    label_base = {"good": 0.85, "acceptable": 0.60, "poor": 0.25, "failed": 0.05, "unknown": None}
    base = label_base.get(entry["label"])
    if base is None:
        return None  # Can't score unknown entries

    score = base

    # Bonuses (+0.05 each, cap at 1.0)
    if entry.get("lint_gate_enforced"):
        score += 0.05
    ratio = entry.get("actionable_findings", 0) / max(entry.get("findings_count", 1), 1)
    score += 0.05 * ratio  # Up to +0.05 for fully actionable findings

    # Penalties
    if entry.get("false_rejection"):
        score -= 0.20
    if entry.get("review_rounds", 1) >= 3:
        score -= 0.10

    return round(min(max(score, 0.0), 1.0), 3)
```

*Why this matters for DSPy:* The Teleprompter's optimizer calls a metric function during compilation with `(example, prediction)` pairs. `calculated_score` is the pre-computed version of that metric stored alongside each example — so Darwin Loop can report trends without re-running Python, and we can filter training examples by quality threshold (e.g., exclude `score < 0.2` as noise).

**Scoring rules:**
- `good`: 1 review round, QA passed first try, no false rejections → ~0.85–0.95
- `acceptable`: 1-2 rounds, minor issues → ~0.55–0.70
- `poor`: 3+ rounds, or QA failed after approval → ~0.15–0.30
- `failed`: Approved code broke production, or multiple false rejections → ~0.05

## engineer-quality.jsonl (planned)

```json
{
  "ts": "ISO-8601",
  "trace_id": "repo_short#ticket — same as review-quality entry for this ticket",
  "commit_hash": "HEAD commit SHA of the engineer's branch",
  "repo": "owner/repo",
  "ticket": "#N",
  "engineer_session": "cron job name",
  "review_rounds_before_approve": 1,
  "lint_clean_first_submit": true,
  "label_updated_correctly": true,
  "scope_respected": true,
  "tests_included": true,
  "local_testing_documented": true,
  "label": "good|acceptable|poor|failed",
  "calculated_score": 0.0
}
```

## qa-quality.jsonl (planned)

```json
{
  "ts": "ISO-8601",
  "trace_id": "repo_short#ticket — same as review-quality entry for this ticket",
  "commit_hash": "experiment branch HEAD SHA at time of QA",
  "repo": "owner/repo",
  "ticket": "#N",
  "qa_session": "cron job name",
  "browser_testing_done": true,
  "experiment_deploy_succeeded": true,
  "real_bugs_found": 0,
  "false_positives": 0,
  "label": "good|acceptable|poor|failed",
  "calculated_score": 0.0
}
```
