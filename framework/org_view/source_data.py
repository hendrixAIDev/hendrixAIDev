"""Load Framework org-view source artifacts."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - exercised through the fallback path in local verification
    yaml = None


@dataclass
class SourceBundle:
    state_files: List[Dict[str, Any]]
    precheck_state: Dict[str, Any]
    queue_by_product: Dict[str, Dict[str, Any]]
    github_issues_by_repo: Optional[Dict[str, Optional[List[Dict[str, Any]]]]]
    source_banner: str


def _workspace_root() -> Path:
    return Path.home() / ".openclaw" / "workspace"


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def _load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is not None:
        return yaml.safe_load(path.read_text()) or {}

    result = subprocess.run(
        ["ruby", "-ryaml", "-rjson", "-e", "print JSON.generate(YAML.safe_load(ARGF.read) || {})", str(path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=8,
    )
    return json.loads(result.stdout or "{}")


def _state_dir(repo_root: Path, workspace_root: Path) -> Tuple[Path, bool]:
    repo_dir = repo_root / "framework" / "board-review" / "state"
    repo_jsons = sorted(repo_dir.glob("*.json"))
    if repo_jsons:
        return repo_dir, False
    return workspace_root / "framework" / "board-review" / "state", True


def _precheck_path(repo_root: Path, workspace_root: Path) -> Tuple[Path, bool]:
    repo_path = repo_root / "framework" / "board-review" / "PRECHECK_STATE.json"
    if repo_path.exists():
        return repo_path, False
    return workspace_root / "framework" / "board-review" / "PRECHECK_STATE.json", True


def _queue_path(task_queue: Optional[str], repo_root: Path, workspace_root: Path) -> Tuple[Optional[Path], bool]:
    if not task_queue:
        return None, False

    repo_path = repo_root / task_queue
    if repo_path.exists():
        return repo_path, False

    workspace_path = workspace_root / task_queue
    if workspace_path.exists():
        return workspace_path, True

    return None, False


def _fetch_open_github_issues(repo: str) -> Optional[List[Dict[str, Any]]]:
    command = [
        "gh",
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--limit",
        "50",
        "--json",
        "number,title,labels",
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=8)
    except (FileNotFoundError, subprocess.SubprocessError):
        return None

    issues = json.loads(result.stdout or "[]")
    for issue in issues:
        issue["labels"] = [label["name"] for label in issue.get("labels", [])]
    return issues


def load_sources(
    repo_root: Path,
    *,
    workspace_root: Optional[Path] = None,
    use_live_github: bool = True,
) -> SourceBundle:
    workspace_root = workspace_root or _workspace_root()

    state_dir, state_from_workspace = _state_dir(repo_root, workspace_root)
    precheck_path, precheck_from_workspace = _precheck_path(repo_root, workspace_root)

    state_files = [_load_json(path) for path in sorted(state_dir.glob("*.json"))]
    precheck_state = _load_json(precheck_path)

    queue_by_product: Dict[str, Dict[str, Any]] = {}
    used_workspace_queue = False
    for product in state_files:
        queue_path, queue_from_workspace = _queue_path(product.get("taskQueue"), repo_root, workspace_root)
        if queue_path is None:
            continue
        queue_by_product[product["slug"]] = _load_yaml(queue_path)
        used_workspace_queue = used_workspace_queue or queue_from_workspace

    github_issues_by_repo: Optional[Dict[str, Optional[List[Dict[str, Any]]]]] = {} if use_live_github else None
    if use_live_github and github_issues_by_repo is not None:
        for product in state_files:
            for repo in product.get("repos", []):
                github_issues_by_repo[repo] = _fetch_open_github_issues(repo)

    banner_parts: list[str] = []
    if state_from_workspace:
        banner_parts.append("Repo snapshot is missing product-state JSON, so rows are using the workspace state mirror.")
    if precheck_from_workspace:
        banner_parts.append("Precheck cache is coming from the workspace mirror.")
    if used_workspace_queue:
        banner_parts.append("Cross-repo queues are resolved from the workspace checkout when the repo snapshot does not contain them.")
    if use_live_github and github_issues_by_repo is not None:
        if any(issues is None for issues in github_issues_by_repo.values()):
            banner_parts.append("Some GitHub issue data was unavailable live, so cached ticket evidence is used where possible.")

    return SourceBundle(
        state_files=state_files,
        precheck_state=precheck_state,
        queue_by_product=queue_by_product,
        github_issues_by_repo=github_issues_by_repo,
        source_banner=" ".join(banner_parts),
    )
