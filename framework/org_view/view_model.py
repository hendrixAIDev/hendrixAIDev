"""Build the read-only org summary and ChurnPilot detail view models for MVP 1."""

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

STAGE_LEGEND = [
    "Discovery",
    "Ready for CTO",
    "In execution",
    "In review",
    "In verification",
    "Awaiting final decision",
    "Blocked",
    "Done",
]

ROLE_ORDER = ["PM", "CTO", "Engineer", "Reviewer", "QA"]

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
    "done",
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


def _precheck_issue_numbers(precheck_state: Dict[str, Any], key: str, repo: str) -> Optional[List[int]]:
    mapping = precheck_state.get(key, {})
    if repo not in mapping:
        return None
    values = mapping.get(repo) or []
    return [int(value) for value in values]


def _issue_context(
    issues: Optional[List[Dict[str, Any]]],
    *,
    cached_actionable_numbers: Optional[List[int]],
    cached_open_numbers: Optional[List[int]],
) -> Tuple[Optional[int], List[str], Set[str], bool, bool, List[int]]:
    if issues is None:
        if cached_actionable_numbers is not None:
            return (
                len(cached_actionable_numbers),
                [],
                set(),
                False,
                True,
                list(cached_actionable_numbers),
            )
        if cached_open_numbers is not None:
            return len(cached_open_numbers), [], set(), False, True, list(cached_open_numbers)
        return None, [], set(), False, False, []

    actionable = [issue for issue in issues if ACTIONABLE_LABELS.intersection(issue.get("labels", []))]
    labels = {label for issue in actionable for label in issue.get("labels", [])}
    titles = [f"#{issue['number']} {issue['title']}" for issue in actionable]
    numbers = [int(issue["number"]) for issue in actionable]
    return len(actionable), titles, labels, True, False, numbers


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


def _stage_summary(stage: str) -> str:
    return {
        "Blocked": "Current state says active work is blocked.",
        "Ready for CTO": "Current ticket or queue state indicates actionable work that likely needs CTO triage or the next dispatch.",
        "In execution": "Current ticket, queue, or dispatch state implies execution work is in flight.",
        "In review": "Current ticket or dispatch state implies work is awaiting or undergoing review.",
        "In verification": "Current ticket or dispatch state implies work is awaiting or undergoing verification.",
        "Awaiting final decision": "Current ticket or queue state implies CTO or JJ decision is the next gating step.",
        "Done": "Current ticket and queue state report no open actionable work.",
        "Discovery": "Current state does not expose a stronger structured workflow signal.",
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
    if not live_github:
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


def _format_timestamp(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _latest_timestamp_text(
    *,
    product_timestamp: Optional[datetime],
    queue_timestamp: Optional[datetime],
    precheck_timestamp: Optional[datetime],
) -> str:
    parts = []
    if product_timestamp is not None:
        parts.append(f"product state {_format_timestamp(product_timestamp)}")
    if queue_timestamp is not None:
        parts.append(f"queue state {_format_timestamp(queue_timestamp)}")
    if precheck_timestamp is not None:
        parts.append(f"precheck {_format_timestamp(precheck_timestamp)}")
    if not parts:
        return "No source refresh timestamp is available from current state artifacts."
    return "Latest source timing: " + " · ".join(parts) + "."


def _snapshot_source_note(bundle: Any, product_slug: str) -> str:
    queue_source = bundle.queue_sources_by_product.get(product_slug)
    queue_note = "queue state"
    if queue_source and queue_source.get("from_workspace"):
        queue_note = "queue state via workspace fallback"
    return "Backed by product state, " + queue_note + ", and GitHub issue/status-label state."


def _raw_status_context(
    *,
    issue_labels: Set[str],
    queue_status: Optional[str],
    blockers: List[str],
    active_dispatches: List[Dict[str, Any]],
    latest_timestamp_text: str,
    cached_ticket_state: bool,
    issue_numbers: List[int],
) -> str:
    fragments: List[str] = []
    if issue_labels:
        fragments.append("ticket labels: " + ", ".join(sorted(issue_labels)))
    if queue_status:
        fragments.append("queue state is " + queue_status.replace("_", " "))
    if issue_numbers:
        issue_refs = ", ".join(f"#{number}" for number in issue_numbers)
        fragments.append("active issue refs: " + issue_refs)
    if active_dispatches:
        fragments.append(
            "dispatches: " + ", ".join(dispatch.get("name", "unnamed dispatch") for dispatch in active_dispatches)
        )
    if blockers:
        fragments.append("blockers: " + "; ".join(str(blocker) for blocker in blockers))
    if cached_ticket_state:
        fragments.append("ticket counts are coming from precheck cache")
    fragments.append(latest_timestamp_text)
    return ". ".join(fragment.rstrip(".") for fragment in fragments if fragment) + "."


def _role_state_reason(state: str) -> str:
    return {
        "idle": "No direct evidence of active work for this role appears in the current state sources.",
        "backlog": "Snapshot wording suggests pending discovery work but not an execution pass.",
        "ready": "Snapshot suggests actionable work is ready for CTO intake.",
        "holding": "Snapshot suggests work is waiting on a CTO or JJ decision.",
        "triaging": "Actionable work appears present, so CTO attention is likely needed next.",
        "coordinating": "The current stage implies work is already moving through execution or downstream gates.",
        "queued": "Role participation is implied as the next step, but active ownership is not proven by current state.",
        "active": "Snapshot wording implies this role's stage is currently active.",
        "returned": "Current ticket or dispatch state implies this role's pass has already handed work onward.",
        "blocked": "A blocker dominates the visible workflow state.",
        "needs_jj": "The next visible gating step appears to require JJ or final decision input.",
    }[state]


def _dispatch_mentions_role(active_dispatches: List[Dict[str, Any]], role_name: str) -> bool:
    role_text = role_name.lower()
    return any(role_text in str(dispatch.get("role", "")).lower() for dispatch in active_dispatches)


def _role_state(role_name: str, stage: str, queue_status: Optional[str], active_dispatches: List[Dict[str, Any]]) -> str:
    dispatch_direct = _dispatch_mentions_role(active_dispatches, role_name)
    if role_name == "PM":
        if queue_status in {"proposed", "triaged"}:
            return "backlog"
        if stage == "Ready for CTO":
            return "ready"
        if stage == "Awaiting final decision":
            return "holding"
        return "idle"
    if role_name == "CTO":
        if stage == "Blocked":
            return "blocked"
        if stage == "Awaiting final decision":
            return "needs_jj"
        if stage == "Ready for CTO":
            return "triaging"
        if stage in {"In execution", "In review", "In verification"}:
            return "coordinating"
        return "idle"
    if role_name == "Engineer":
        if stage == "Blocked":
            return "blocked"
        if dispatch_direct or stage == "In execution":
            return "active"
        if stage in {"In review", "In verification", "Awaiting final decision"}:
            return "returned"
        return "idle"
    if role_name == "Reviewer":
        if stage == "Blocked":
            return "blocked"
        if dispatch_direct or stage == "In review":
            return "active"
        if stage in {"In verification", "Awaiting final decision"}:
            return "returned"
        return "idle"
    if stage == "Blocked":
        return "blocked"
    if dispatch_direct or stage == "In verification":
        return "active"
    if stage == "Awaiting final decision":
        return "returned"
    return "idle"


def _role_source_note(
    role_name: str,
    *,
    active_dispatches: List[Dict[str, Any]],
    issue_labels: Set[str],
    cached_ticket_state: bool,
) -> str:
    if _dispatch_mentions_role(active_dispatches, role_name):
        return "Direct from the current active dispatch metadata."
    if issue_labels:
        return "Inferred from ticket labels and shared stage mapping."
    if cached_ticket_state:
        return "Inferred from cached ticket state plus queue and product-state context."
    return "Inferred from queue and product-state context because no direct active dispatch is present."


def _product_contexts(bundle: Any, now: datetime) -> Dict[str, Dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    precheck_timestamp = _parse_timestamp(bundle.precheck_state.get("lastCheckTime"))
    contexts: Dict[str, Dict[str, Any]] = {}
    for product in sorted(bundle.state_files, key=lambda item: item["product"].lower()):
        repo = (product.get("repos") or ["Unknown repo"])[0]
        queue_data = bundle.queue_by_product.get(product["slug"])
        queue_status = _queue_status(queue_data, repo)

        live_issues = None
        if bundle.github_issues_by_repo is not None:
            live_issues = bundle.github_issues_by_repo.get(repo)
        cached_actionable_numbers = _precheck_issue_numbers(
            bundle.precheck_state, "actionableIssueNumbersByRepo", repo
        )
        cached_open_numbers = _precheck_issue_numbers(bundle.precheck_state, "openIssuesByRepo", repo)
        issue_count, issue_titles, issue_labels, live_github, cached_ticket_state, issue_numbers = _issue_context(
            live_issues,
            cached_actionable_numbers=cached_actionable_numbers,
            cached_open_numbers=cached_open_numbers,
        )

        last_result = product.get("lastResult")
        blockers = product.get("currentBlockers") or []
        active_dispatches = product.get("activeDispatches") or []
        has_blocker = bool(blockers)
        precheck_actionable = bool(cached_actionable_numbers)
        queue_timestamp = _parse_timestamp(queue_data.get("updated_at") if queue_data else None)
        latest_timestamp = max(
            [
                value
                for value in (
                    _parse_timestamp(product.get("lastRunAt")),
                    queue_timestamp,
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
            and (queue_status in {None, "done"})
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
        latest_timestamp_text = _latest_timestamp_text(
            product_timestamp=_parse_timestamp(product.get("lastRunAt")),
            queue_timestamp=queue_timestamp,
            precheck_timestamp=precheck_timestamp,
        )

        contexts[product["slug"]] = {
            "product_key": product["slug"],
            "product_name": product["product"],
            "repo": repo,
            "primary_readme": product.get("primaryReadme"),
            "task_queue": product.get("taskQueue"),
            "queue_data": queue_data,
            "queue_status": queue_status,
            "issue_count": issue_count,
            "issue_titles": issue_titles,
            "issue_labels": issue_labels,
            "issue_numbers": issue_numbers,
            "live_github": live_github,
            "cached_ticket_state": cached_ticket_state,
            "last_result": last_result,
            "blockers": blockers,
            "active_dispatches": active_dispatches,
            "stale": stale,
            "sparse": sparse,
            "stage": stage,
            "latest_timestamp_text": latest_timestamp_text,
            "detail_page_available": product["slug"] == "churnpilot",
            "source_confidence_note": _confidence_note(
                live_github=live_github,
                issue_count=issue_count,
                used_queue=queue_data is not None,
                inferred=inferred,
                stale=stale,
                sparse=sparse,
            ),
            "snapshot_source": _snapshot_source_note(bundle, product["slug"]),
            "raw_status_context": _raw_status_context(
                issue_labels=issue_labels,
                queue_status=queue_status,
                blockers=blockers,
                active_dispatches=active_dispatches,
                latest_timestamp_text=latest_timestamp_text,
                cached_ticket_state=cached_ticket_state,
                issue_numbers=issue_numbers,
            ),
        }
    return contexts


def _summary_row(context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "product_key": context["product_key"],
        "product_name": context["product_name"],
        "repo": context["repo"],
        "current_status_text": _current_status_text(
            context["issue_titles"], context["queue_status"], context["last_result"]
        ),
        "normalized_stage_group": context["stage"],
        "actionability_signal": _actionability(context["stage"], context["sparse"]),
        "next_attention_text": _next_attention(context["stage"]),
        "open_actionable_ticket_count": context["issue_count"],
        "active_issue_titles": context["issue_titles"],
        "detail_page_available": context["detail_page_available"],
        "source_confidence_note": context["source_confidence_note"],
    }


def _churnpilot_detail(context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if context is None:
        return None

    role_chips = []
    for role_name in ROLE_ORDER:
        state = _role_state(role_name, context["stage"], context["queue_status"], context["active_dispatches"])
        role_chips.append(
            {
                "role_name": role_name,
                "role_state": state,
                "role_state_reason": _role_state_reason(state),
                "role_source_note": _role_source_note(
                    role_name,
                    active_dispatches=context["active_dispatches"],
                    issue_labels=context["issue_labels"],
                    cached_ticket_state=context["cached_ticket_state"],
                ),
            }
        )

    detail_status = _current_status_text(context["issue_titles"], context["queue_status"], context["last_result"])
    fidelity_fragments = [context["source_confidence_note"]]
    if context["detail_page_available"]:
        fidelity_fragments.append("detail view is intentionally read-only")

    return {
        "product_key": context["product_key"],
        "product_name": context["product_name"],
        "repo": context["repo"],
        "primary_readme": context["primary_readme"],
        "task_queue": context["task_queue"],
        "detail_scope_label": "MVP 1 pilot detail page",
        "snapshot_source": context["snapshot_source"],
        "snapshot_timestamp_text": context["latest_timestamp_text"],
        "source_fidelity_note": "; ".join(fragment for fragment in fidelity_fragments if fragment),
        "active_issue_count": 0 if context["issue_count"] is None else context["issue_count"],
        "active_issue_titles": context["issue_titles"],
        "active_issue_numbers": context["issue_numbers"],
        "current_status_text": detail_status,
        "normalized_stage_group": context["stage"],
        "stage_summary_text": _stage_summary(context["stage"]),
        "next_attention_text": _next_attention(context["stage"]),
        "open_actionable_ticket_count": 0 if context["issue_count"] is None else context["issue_count"],
        "role_chips": role_chips,
        "normalized_stage_legend": list(STAGE_LEGEND),
        "raw_status_context": context["raw_status_context"],
    }


def build_org_view(repo_root: Path, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    bundle = load_sources(repo_root)
    contexts = _product_contexts(bundle, now or datetime.now(timezone.utc))
    rows = [_summary_row(context) for _, context in sorted(contexts.items(), key=lambda item: item[1]["product_name"].lower())]

    return {
        "rows": rows,
        "source_banner": bundle.source_banner,
        "churnpilot_detail": _churnpilot_detail(contexts.get("churnpilot")),
    }


def build_org_summary(repo_root: Path, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    summary = build_org_view(repo_root, now=now)
    return {"rows": summary["rows"], "source_banner": summary["source_banner"]}


def build_churnpilot_detail(repo_root: Path, *, now: Optional[datetime] = None) -> Dict[str, Any]:
    summary = build_org_view(repo_root, now=now)
    return summary["churnpilot_detail"]
