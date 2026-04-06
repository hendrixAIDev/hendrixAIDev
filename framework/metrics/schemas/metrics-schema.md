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

## engineer-quality.jsonl

```json
{
  "ts": "ISO-8601",
  "trace_id": "repo_short#ticket — same as review-quality entry for this ticket",
  "commit_hash": "HEAD commit SHA of the engineer's branch",
  "repo": "owner/repo",
  "ticket": "#N",
  "ticket_title": "Short title",
  "engineer_session": "cron job name or session label",
  "engineer_role": "fullstack|backend|frontend",
  "engineer_rounds": 1,
  "lint_clean_first_submit": true,
  "label_updated_correctly": true,
  "scope_respected": true,
  "tests_included": true,
  "tests_match_acceptance_criteria": true,
  "local_testing_documented": true,
  "streamlit_gotcha_hit": false,
  "gotcha_category": null,
  "label": "good|acceptable|poor|failed",
  "calculated_score": 0.0,
  "notes": "Optional context"
}
```

### `engineer_role` — DSPy Conditioning Field

Tracks whether the engineer was dispatched as `fullstack`, `backend`, or `frontend`. Enables:
- Per-role quality analysis (fullstack vs backend pass rates)
- Conditional DSPy optimization ("when role=fullstack, emphasize Streamlit patterns")
- Role selection improvement (did the right role get dispatched?)

### `streamlit_gotcha_hit` / `gotcha_category`

Flags whether the engineer hit a known Streamlit pitfall from `framework/knowledge/streamlit-gotchas.md`. Categories: `session_state`, `module_reload`, `button_rerun`, `tabs_fragments`, `thread_safety`, `css`, `deployment`, `caching`, `persistence`, `pages_dir`. Enables tracking which gotchas still trip engineers despite documentation.

### Engineer Score Calculation

```python
def calculate_engineer_score(entry: dict) -> float:
    label_base = {"good": 0.85, "acceptable": 0.60, "poor": 0.25, "failed": 0.05}
    base = label_base.get(entry["label"])
    if base is None:
        return None

    score = base

    # Bonuses
    if entry.get("lint_clean_first_submit"):
        score += 0.05
    if entry.get("tests_match_acceptance_criteria"):
        score += 0.05
    if entry.get("local_testing_documented"):
        score += 0.03

    # Penalties
    if entry.get("engineer_rounds", 1) >= 3:
        score -= 0.15
    if not entry.get("scope_respected", True):
        score -= 0.10
    if entry.get("streamlit_gotcha_hit"):
        score -= 0.05  # Known pattern they should have avoided

    return round(min(max(score, 0.0), 1.0), 3)
```

## qa-quality.jsonl

```json
{
  "ts": "ISO-8601",
  "trace_id": "repo_short#ticket — same as review-quality entry for this ticket",
  "commit_hash": "experiment branch HEAD SHA at time of QA",
  "repo": "owner/repo",
  "ticket": "#N",
  "ticket_title": "Short title",
  "qa_session": "cron job name or session label",
  "qa_rounds": 1,
  "browser_testing_done": true,
  "experiment_deploy_succeeded": true,
  "experiment_endpoint_verified": true,
  "real_bugs_found": 0,
  "false_positives": 0,
  "tests_run": true,
  "test_count": 0,
  "new_test_count": 0,
  "regressions_found": 0,
  "label": "good|acceptable|poor|failed",
  "calculated_score": 0.0,
  "notes": "Optional context"
}
```

### QA Score Calculation

```python
def calculate_qa_score(entry: dict) -> float:
    label_base = {"good": 0.85, "acceptable": 0.60, "poor": 0.25, "failed": 0.05}
    base = label_base.get(entry["label"])
    if base is None:
        return None

    score = base

    # Bonuses
    if entry.get("browser_testing_done"):
        score += 0.05
    if entry.get("experiment_endpoint_verified"):
        score += 0.05
    if entry.get("regressions_found", 0) == 0 and entry.get("tests_run"):
        score += 0.03

    # Penalties
    if entry.get("false_positives", 0) >= 2:
        score -= 0.10  # QA raising false alarms
    if entry.get("qa_rounds", 1) >= 3:
        score -= 0.10
    if not entry.get("experiment_deploy_succeeded", True):
        score -= 0.05  # Deploy failure not QA's fault, but track it

    return round(min(max(score, 0.0), 1.0), 3)
```

## triage-quality.jsonl

```json
{
  "ts": "ISO-8601",
  "trace_id": "repo_short#ticket",
  "repo": "owner/repo",
  "ticket": "#N",
  "ticket_title": "Short title",
  "cto_session": "cron job name or session label",
  "correct_role_dispatched": true,
  "acceptance_tests_added": true,
  "dependencies_checked": true,
  "evolver_consulted": true,
  "round_count_respected": true,
  "total_rounds_to_close": 1,
  "escalated_appropriately": true,
  "label": "good|acceptable|poor|failed",
  "calculated_score": 0.0,
  "notes": "Optional context"
}
```

### Triage Score Calculation

```python
def calculate_triage_score(entry: dict) -> float:
    label_base = {"good": 0.85, "acceptable": 0.60, "poor": 0.25, "failed": 0.05}
    base = label_base.get(entry["label"])
    if base is None:
        return None

    score = base

    # Bonuses
    if entry.get("correct_role_dispatched"):
        score += 0.05
    if entry.get("acceptance_tests_added"):
        score += 0.05
    if entry.get("evolver_consulted"):
        score += 0.03

    # Penalties
    if entry.get("total_rounds_to_close", 1) >= 4:
        score -= 0.15
    if not entry.get("correct_role_dispatched", True):
        score -= 0.10
    if not entry.get("round_count_respected", True):
        score -= 0.20  # Dispatched beyond 3-round limit

    return round(min(max(score, 0.0), 1.0), 3)
```
```
