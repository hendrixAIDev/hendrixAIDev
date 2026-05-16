from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from framework.org_view.source_data import load_sources
from framework.org_view.view_model import build_churnpilot_detail, build_org_summary


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, value in payload.items():
        if key != "tasks":
            lines.append(f"{key}: {json.dumps(value)}")
            continue
        lines.append("tasks:")
        for task in value:
            lines.append(f"  - id: {task['id']}")
            lines.append(f"    status: {task['status']}")
            lines.append(f"    github_issue: {json.dumps(task['github_issue'])}")
    path.write_text("\n".join(lines) + "\n")


def _repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    state_dir = repo_root / "framework" / "board-review" / "state"

    _write_json(
        state_dir / "churnpilot.json",
        {
            "product": "ChurnPilot",
            "slug": "churnpilot",
            "repos": ["hendrixAIDev/churn_copilot_hendrix"],
            "taskQueue": "projects/churn_copilot/plans/task-queue.yaml",
            "lastRunAt": "2026-05-16T06:00:00Z",
            "lastResult": "No open actionable tickets in latest ticket/precheck state.",
            "currentBlockers": [],
            "activeDispatches": [],
        },
    )
    _write_json(
        state_dir / "framework.json",
        {
            "product": "Framework",
            "slug": "framework",
            "repos": ["hendrixAIDev/hendrixAIDev"],
            "taskQueue": "framework/plans/task_queue/tasks.yaml",
            "lastRunAt": "2026-05-16T06:06:45Z",
            "lastResult": "Framework #31 is open with status:in-progress.",
            "currentBlockers": [],
            "activeDispatches": [{"name": "eng-fw31-org-summary-r1"}],
        },
    )
    _write_json(
        state_dir / "statuspulse.json",
        {
            "product": "StatusPulse",
            "slug": "statuspulse",
            "repos": ["hendrixAIDev/statuspulse"],
            "taskQueue": None,
            "lastRunAt": None,
            "lastResult": "Open feature tickets remain blocked in the current fleet snapshot.",
            "currentBlockers": ["Feature tickets are blocked."],
            "activeDispatches": [],
        },
    )

    _write_json(
        repo_root / "framework" / "board-review" / "PRECHECK_STATE.json",
        {
            "lastCheckTime": "2026-05-16T06:06:23Z",
            "actionableIssueNumbersByRepo": {"hendrixAIDev/hendrixAIDev": [31]},
        },
    )

    _write_yaml(
        repo_root / "framework" / "plans" / "task_queue" / "tasks.yaml",
        {
            "repo": "hendrixAIDev/hendrixAIDev",
            "updated_at": "2026-05-15T23:05:00-07:00",
            "tasks": [{"id": "f1", "status": "in_progress", "github_issue": "hendrixAIDev/hendrixAIDev#31"}],
        },
    )

    workspace_root = tmp_path / "workspace"
    _write_yaml(
        workspace_root / "projects" / "churn_copilot" / "plans" / "task-queue.yaml",
        {
            "repo": "hendrixAIDev/churn_copilot_hendrix",
            "updated_at": "2026-05-15T22:28:00-07:00",
            "tasks": [{"id": "cp1", "status": "done", "github_issue": "hendrixAIDev/churn_copilot_hendrix#223"}],
        },
    )
    return repo_root


def test_load_sources_prefers_repo_state_and_uses_workspace_queue_fallback(tmp_path: Path) -> None:
    repo_root = _repo_root(tmp_path)
    workspace_root = tmp_path / "workspace"

    sources = load_sources(repo_root, workspace_root=workspace_root, use_live_github=False)

    assert [item["slug"] for item in sources.state_files] == ["churnpilot", "framework", "statuspulse"]
    assert "Cross-repo queues are resolved from the workspace checkout" in sources.source_banner
    assert sources.queue_by_product["churnpilot"]["repo"] == "hendrixAIDev/churn_copilot_hendrix"


def test_build_org_summary_maps_stage_detail_and_sparse_confidence(tmp_path: Path, monkeypatch) -> None:
    repo_root = _repo_root(tmp_path)
    workspace_root = tmp_path / "workspace"

    import framework.org_view.source_data as source_data

    monkeypatch.setattr(source_data, "_workspace_root", lambda: workspace_root)
    monkeypatch.setattr(
        source_data,
        "_fetch_open_github_issues",
        lambda repo: {
            "hendrixAIDev/hendrixAIDev": [
                {
                    "number": 31,
                    "title": "Deliver the org-first default summary",
                    "labels": ["status:in-progress", "priority:high"],
                }
            ],
            "hendrixAIDev/churn_copilot_hendrix": [],
            "hendrixAIDev/statuspulse": [
                {"number": 32, "title": "Blocked rollout", "labels": ["status:blocked"]}
            ],
        }.get(repo),
    )

    summary = build_org_summary(repo_root, now=datetime(2026, 5, 16, 6, 10, tzinfo=timezone.utc))
    rows = {row["product_key"]: row for row in summary["rows"]}

    assert rows["framework"]["normalized_stage_group"] == "In execution"
    assert rows["framework"]["open_actionable_ticket_count"] == 1
    assert rows["framework"]["detail_page_available"] is False
    assert rows["framework"]["current_status_text"].startswith("#31 Deliver the org-first default summary")

    assert rows["churnpilot"]["normalized_stage_group"] == "Done"
    assert rows["churnpilot"]["actionability_signal"] == "idle"
    assert rows["churnpilot"]["detail_page_available"] is True

    assert rows["statuspulse"]["normalized_stage_group"] == "Blocked"
    assert rows["statuspulse"]["actionability_signal"] == "blocked"


def test_build_churnpilot_detail_shows_all_roles_even_when_idle(tmp_path: Path, monkeypatch) -> None:
    repo_root = _repo_root(tmp_path)
    workspace_root = tmp_path / "workspace"

    import framework.org_view.source_data as source_data

    monkeypatch.setattr(source_data, "_workspace_root", lambda: workspace_root)
    monkeypatch.setattr(
        source_data,
        "_fetch_open_github_issues",
        lambda repo: {
            "hendrixAIDev/hendrixAIDev": [],
            "hendrixAIDev/churn_copilot_hendrix": [],
            "hendrixAIDev/statuspulse": [],
        }.get(repo),
    )

    detail = build_churnpilot_detail(repo_root, now=datetime(2026, 5, 16, 6, 10, tzinfo=timezone.utc))

    assert detail["product_key"] == "churnpilot"
    assert detail["normalized_stage_group"] == "Done"
    assert detail["active_issue_count"] == 0
    assert detail["open_actionable_ticket_count"] == 0
    assert detail["snapshot_source"].startswith("Backed by product state")
    assert len(detail["role_chips"]) == 5
    assert [chip["role_name"] for chip in detail["role_chips"]] == [
        "PM",
        "CTO",
        "Engineer",
        "Reviewer",
        "QA",
    ]
    assert all(chip["role_state"] == "idle" for chip in detail["role_chips"])
    assert all(chip["role_state_reason"] for chip in detail["role_chips"])
    assert all(chip["role_source_note"] for chip in detail["role_chips"])
    assert "queue state is done" in detail["raw_status_context"].lower()


def test_build_churnpilot_detail_keeps_cached_open_issue_context_out_of_actionable_counts(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = _repo_root(tmp_path)
    workspace_root = tmp_path / "workspace"

    import framework.org_view.source_data as source_data

    _write_json(
        repo_root / "framework" / "board-review" / "PRECHECK_STATE.json",
        {
            "lastCheckTime": "2026-05-16T06:06:23Z",
            "openIssuesByRepo": {"hendrixAIDev/churn_copilot_hendrix": [223, 224]},
        },
    )

    monkeypatch.setattr(source_data, "_workspace_root", lambda: workspace_root)
    monkeypatch.setattr(source_data, "_fetch_open_github_issues", lambda repo: None)

    detail = build_churnpilot_detail(repo_root, now=datetime(2026, 5, 16, 6, 10, tzinfo=timezone.utc))

    assert detail["active_issue_count"] == 2
    assert detail["open_actionable_ticket_count"] is None
    assert detail["active_issue_titles"] == []
    assert detail["active_issue_numbers"] == [223, 224]
    assert "#223" in detail["raw_status_context"]
    assert "cached" in detail["source_fidelity_note"].lower()
