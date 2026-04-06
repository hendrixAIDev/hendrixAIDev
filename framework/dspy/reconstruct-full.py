#!/usr/bin/env python3
"""Full reconstruction: pull ALL closed tickets from GitHub repos and build
DSPy training data using the cleaner stage-aware builders from reconstruct.py.

Usage:
    python reconstruct-full.py [--dry-run] [--stage all|code-review|engineer|qa|triage]
"""

import json
import time
from pathlib import Path

from reconstruct import STAGE_BUILDERS
import subprocess

OUTPUT_DIR = Path(__file__).parent / "training-data"

REPOS = [
    "hendrixAIDev/churn_copilot_hendrix",
    "hendrixAIDev/character-life-sim",
    "hendrixAIDev/hendrixAIDev",
    "zrjaa1/openclaw-assistant",
    "hendrixAIDev/hendrixaidev.github.io",
]

ISSUE_FIELDS = "number,title,body,labels,comments,state,closedAt,createdAt,author"


def fetch_all_closed_issues(repo: str) -> list[dict]:
    print(f"  Fetching closed issues from {repo}...")
    result = subprocess.run(
        ["gh", "issue", "list", "--repo", repo, "--state", "closed", "--limit", "500", "--json", ISSUE_FIELDS],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        print(f"  WARN: Failed to fetch {repo}: {result.stderr.strip()[:120]}")
        return []
    issues = json.loads(result.stdout)
    print(f"  Got {len(issues)} closed issues from {repo}")
    return issues


def derive_quality_score(issue: dict, repo: str) -> float:
    score = 0.0
    body = issue.get("body") or ""
    labels = [l.get("name", "") for l in issue.get("labels", [])]
    comments = issue.get("comments", [])

    if issue.get("state") == "CLOSED":
        score += 0.2
    if len(body) > 100:
        score += 0.15
    if len(body) > 500:
        score += 0.1
    if any(marker in body for marker in ["- [ ]", "- [x]", "## ", "### ", "acceptance", "Acceptance", "test_"]):
        score += 0.15
    if labels:
        score += 0.1
    if any(l in labels for l in ["bug", "feature", "enhancement", "fix", "priority:high", "priority:medium"]):
        score += 0.1
    if len(comments) >= 2:
        score += 0.1
    if len(comments) >= 5:
        score += 0.1
    impl_keywords = ["merge", "commit", "fix", "implement", "deploy", "test", "pass", "approved", "request changes"]
    for c in comments:
        cbody = c.get("body", "")
        if any(kw.lower() in cbody.lower() for kw in impl_keywords):
            score += 0.05
            break
    return min(score, 1.0)


def issue_to_metric_record(repo: str, issue: dict, score: float) -> dict:
    labels = [l.get("name", "") for l in issue.get("labels", [])]
    comments = issue.get("comments", [])
    comments_text = "\n---\n".join(c.get("body", "")[:2000] for c in comments if c.get("body"))
    title = issue.get("title", "") or ""
    body = issue.get("body", "") or ""
    lower = f"{title}\n{body}\n{comments_text}".lower()

    real_bugs = 0
    if "qa fail" in lower or "failed" in lower or "bug" in lower or "regression" in lower:
        real_bugs = 1

    return {
        "repo": repo,
        "ticket": f"#{issue['number']}",
        "ticket_title": title,
        "trace_id": f"{repo.split('/')[-1]}#{issue['number']}",
        "calculated_score": score,
        "label": "good" if score >= 0.85 else "acceptable" if score >= 0.6 else "poor",
        "notes": comments_text[:4000],
        "verdict": "REJECT" if "request changes" in lower or "review rejected" in lower else "APPROVE",
        "findings_count": comments_text.lower().count("- "),
        "actionable_findings": 1 if "request changes" in lower or "scope violation" in lower else 0,
        "scope_violation_flagged": "scope violation" in lower,
        "qa_passed_first_try": not any(tok in lower for tok in ["qa fail", "failed qa", "regression", "bug found"]),
        "review_comment": comments_text[:2500],
        "real_bugs_found": real_bugs,
        "regressions_found": real_bugs,
        "tests_match_acceptance_criteria": "test_" in lower or "pytest" in lower,
        "scope_respected": "scope violation" not in lower,
        "local_testing_documented": "localhost:" in lower,
        "correct_role_dispatched": True,
        "acceptance_tests_added": "acceptance" in body.lower() or "test_" in body.lower(),
        "engineer_role": "frontend" if any(tok in lower for tok in ["ui", "frontend", "streamlit", "page"]) else "backend" if any(tok in lower for tok in ["api", "database", "webhook"]) else "fullstack",
    }


def dedupe_examples(examples: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for ex in examples:
        key = (
            ex.get("_repo"),
            ex.get("_ticket"),
            ex.get("verdict"),
            ex.get("qa_verdict"),
            ex.get("engineer_role"),
            (ex.get("review_comment") or ex.get("dispatch_note") or ex.get("verification_report") or ex.get("implementation_plan") or "")[:200],
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(ex)
    return out


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Full reconstruction from GitHub repos using clean stage builders")
    parser.add_argument("--stage", default="all", choices=["all"] + list(STAGE_BUILDERS.keys()))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--min-score", type=float, default=0.3)
    args = parser.parse_args()

    stages = list(STAGE_BUILDERS.keys()) if args.stage == "all" else [args.stage]

    print("Fetching all closed issues from GitHub...\n")
    all_issues: list[tuple[str, dict, float]] = []
    for repo in REPOS:
        issues = fetch_all_closed_issues(repo)
        for issue in issues:
            body = issue.get("body") or ""
            if len(body.strip()) < 20:
                continue
            score = derive_quality_score(issue, repo)
            if score >= args.min_score:
                all_issues.append((repo, issue, score))
        time.sleep(0.5)

    print(f"\nUsable closed issues: {len(all_issues)}")
    if args.dry_run:
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    for stage in stages:
        builder = STAGE_BUILDERS[stage]
        examples = []
        for repo, issue, score in all_issues:
            record = issue_to_metric_record(repo, issue, score)
            built = builder(record)
            if isinstance(built, list):
                examples.extend(built)
            elif built:
                examples.append(built)
        examples = dedupe_examples(examples)
        output_path = OUTPUT_DIR / f"{stage}-training-full.jsonl"
        with open(output_path, "w") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")
        print(f"{stage}: {len(examples)} examples → {output_path}")

    print("\nFull reconstruction complete.")


if __name__ == "__main__":
    main()
