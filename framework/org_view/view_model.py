"""Build the read-only org summary view model for MVP 1."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from framework.org_view.source_data import load_sources

ACTIONABLE_LABELS = {
    "status:new",
    "status:in-progress",
    "status:review",
    "status:verification",
    "status:cto-review",
    "status:needs-jj",
    "status:blocked",
}

STAGE_PRECEDENCE = [
    ("Blocked", lambda ctx: ctx["has_blocker"] or ctx["has_issue_label"]("status:blocked") or ctx["queue_status"] == "blocked"),
    (
        "Awaiting final decision",
        lambda ctx: ctx["has_issue_label"]("status:needs-jj")
        or ctx["has_issue_label"]("status:cto-review")
        or ctx["queue_status"] == "needs_human",
    ),
    ("In review", lambda ctx: ctx["has_issue_label"]("status:review")),
    ("In verification", lambda ctx: ctx["has_issue_label"]("status:verification")),
    (
        "In execution",
        lambda ctx: ctx["has_issue_label"]("status:in-progress")
        or ctx["queue_status"] == "in_progress"
        or bool(ctx["active_dispatches"]),
    ),
    (
        "Ready for CTO",
        lambda ctx: ctx["has_issue_label"]("status:new")
        or ctx["queue_status"] in {"ticketed", "triaged"}
        or ctx["precheck_actionable"],
    ),
    ("Discovery", lambda ctx: ctx["queue_status"] == "proposed"),
    ("Done", lambda ctx: ctx["all_known_work_done"]),
]

QUEUE_PRECEDENCE = [
    "blocked",
    "needs_human",
    "in_progress",
    "ticketed",
    "triaged",
    "proposed",
]


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _queue_status(queue_data: Optional[Dict[str, Any]], repo: str) -> Optional[str]:
    if not queue_data:
        return None

    tasks = queue_data.get("tasks", [])
    if queue_data.get("repo") == repo:
        matching_tasks = tasks
    else:
        matching_tasks = [task for task in tasks if repo in str(task)]

    statuses = {task.get("status") for task in matching_tasks if task.get("status")}
    for status in QUEUE_PRECEDENCE:
        if status in statuses:
            return status

    return None


def _issue_context(issues: Optional[List[Dict[str, Any]]]) -> Tuple[Optional[int], List[str], Set[str], bool]:
    if issues is None:
        return None, [], set(), False

    actionable = [issue for issue in issues if ACTIONABLE_LABELS.intersection(issue.get("labels", []))]
    labels = {label for issue in actionable for label in issue.get("labels", [])}
    titles = [f"#{issue['number']} {issue['title']}" for issue in actionable]
    return len(actionable), titles, labels, True


def _current_status_text(issue_titles: List[str], queue_status: Optional[str], last_result: Optional[str]) -> str:
    if issue_titles:
        return issue_titles[0]
    if queue_status:
        return f"Queue state is {queue_status.replace('_', ' ')}."
    if last_result:
        return last_result
    return "No current status text available from product state or tickets."


def _next_attention(stage: str) -> str:
    return {
        "Ready for CTO": "CTO should review the product's next actionable work.",
        "In execution": "Execution is in flight; next attention is the result of the active pass.",
        "In review": "Review outcome is the next gating step.",
        "In verification": "Verification outcome is the next gating step.",
        "Awaiting final decision": "Final decision is the next gating step.",
        "Blocked": "Resolve the blocker before work can advance.",
        "Done": "No immediate action is visible from current product and ticket state.",
        "Discovery": "Snapshot is too thin to name the next step confidently.",
    }[stage]


def _actionability(stage: str, sparse: bool) -> str:
    if stage == "Blocked":
        return "blocked"
    if stage == "Done":
        return "idle"
    if sparse and stage == "Discovery":
        return "unknown"
    return "action needed"


def _confidence_note(
    *,
    live_github: bool,
    issue_count: Optional[int],
    used_queue: bool,
    inferred: bool,
    stale: bool,
    sparse: bool,
) -> str:
    notes: list[str] = []
    if issue_count is None and not live_github:
        notes.append("ticket state cached")
    if not used_queue:
        notes.append("queue sparse")
    if inferred:
        notes.append("stage inferred")
    if stale:
        notes.append("state may be stale")
    if sparse:
        notes.append("snapshot thin")
    return ", ".join(notes) if notes else "direct from current state sources"


def build_org_summary(repo_root: Path, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    bundle = load_sources(repo_root)
    now = now or datetime.now(timezone.utc)
    precheck_timestamp = _parse_timestamp(bundle.precheck_state.get("lastCheckTime"))
    actionable_cache = bundle.precheck_state.get("actionableIssueNumbersByRepo", {})

    rows: List[Dict[str, Any]] = []
    for product in sorted(bundle.state_files, key=lambda item: item["product"].lower()):
        repo = (product.get("repos") or ["Unknown repo"])[0]
        queue_data = bundle.queue_by_product.get(product["slug"])
        queue_status = _queue_status(queue_data, repo)

        live_issues = None
        if bundle.github_issues_by_repo is not None:
            live_issues = bundle.github_issues_by_repo.get(repo)
        issue_count, issue_titles, issue_labels, live_github = _issue_context(live_issues)

        last_result = product.get("lastResult")
        blockers = product.get("currentBlockers") or []
        active_dispatches = product.get("activeDispatches") or []
        has_blocker = bool(blockers)
        precheck_actionable = bool(actionable_cache.get(repo))
        latest_timestamp = max(
            [
                value
                for value in (
                    _parse_timestamp(product.get("lastRunAt")),
                    _parse_timestamp(queue_data.get("updated_at") if queue_data else None),
                    precheck_timestamp,
                )
                if value is not None
            ],
            default=None,
        )
        stale = latest_timestamp is None or (now - latest_timestamp).total_seconds() > 86400

        all_known_work_done = (
            not has_blocker
            and not active_dispatches
            and not issue_labels
            and (queue_status is None)
            and (
                "no open actionable" in (last_result or "").lower()
                or "no-op board-review pass" in (last_result or "").lower()
            )
        )

        context = {
            "has_blocker": has_blocker,
            "queue_status": queue_status,
            "active_dispatches": active_dispatches,
            "precheck_actionable": precheck_actionable,
            "all_known_work_done": all_known_work_done,
            "has_issue_label": lambda label: label in issue_labels,
        }

        stage = "Discovery"
        for candidate, predicate in STAGE_PRECEDENCE:
            if predicate(context):
                stage = candidate
                break

        sparse = not issue_titles and queue_status is None and not active_dispatches and not blockers
        inferred = not issue_labels and stage in {"Discovery", "Done", "In execution", "Blocked"}

        rows.append(
            {
                "product_key": product["slug"],
                "product_name": product["product"],
                "repo": repo,
                "current_status_text": _current_status_text(issue_titles, queue_status, last_result),
                "normalized_stage_group": stage,
                "actionability_signal": _actionability(stage, sparse),
                "next_attention_text": _next_attention(stage),
                "open_actionable_ticket_count": issue_count,
                "active_issue_titles": issue_titles,
                "detail_page_available": product["slug"] == "churnpilot",
                "source_confidence_note": _confidence_note(
                    live_github=live_github,
                    issue_count=issue_count,
                    used_queue=queue_data is not None,
                    inferred=inferred,
                    stale=stale,
                    sparse=sparse,
                ),
            }
        )

    return {
        "rows": rows,
        "source_banner": bundle.source_banner,
    }
