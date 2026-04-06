#!/usr/bin/env python3
"""Reconstruct full DSPy training examples from GitHub issues + git history.

Reads existing quality JSONL files, fetches ticket bodies from GitHub,
and writes enriched JSONL with the fields DSPy signatures actually need.

Usage:
    python reconstruct.py [--dry-run] [--stage all|code-review|engineer|qa|triage]
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

METRICS_DIR = Path(__file__).parent.parent / "metrics"
OUTPUT_DIR = Path(__file__).parent / "training-data"

# Map messy repo names to canonical owner/repo
REPO_NORMALIZE = {
    "churn_copilot_hendrix": "hendrixAIDev/churn_copilot_hendrix",
    "character-life-sim": "hendrixAIDev/character-life-sim",
    "openclaw-assistant": "zrjaa1/openclaw-assistant",
    "hendrixAIDev": "hendrixAIDev/hendrixAIDev",
}

STAGE_FILES = {
    "code-review": "review-quality.jsonl",
    "engineer": "engineer-quality.jsonl",
    "qa": "qa-quality.jsonl",
    "triage": "triage-quality.jsonl",
}

# Cache fetched issues to avoid redundant API calls
_issue_cache: dict[str, dict] = {}


def normalize_repo(repo: str) -> str:
    """Normalize repo name to owner/repo format."""
    return REPO_NORMALIZE.get(repo, repo)


def normalize_ticket(ticket) -> str | None:
    """Extract issue number from ticket field (e.g., '#45' -> '45')."""
    t = str(ticket).strip().lstrip("#")
    if t.isdigit():
        return t
    return None


def fetch_issue(repo: str, number: str) -> dict | None:
    """Fetch a GitHub issue via gh CLI. Returns parsed JSON or None."""
    cache_key = f"{repo}#{number}"
    if cache_key in _issue_cache:
        return _issue_cache[cache_key]

    try:
        result = subprocess.run(
            ["gh", "issue", "view", number, "--repo", repo, "--json",
             "title,body,labels,comments,closedAt,state"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            _issue_cache[cache_key] = data
            return data
        else:
            print(f"  WARN: gh issue view {repo}#{number} failed: {result.stderr.strip()[:80]}")
            return None
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f"  WARN: Error fetching {repo}#{number}: {e}")
        return None


def fetch_issue_comments_text(repo: str, number: str) -> str:
    """Get review comments from the issue (code review findings, QA reports, etc.)."""
    issue = fetch_issue(repo, number)
    if not issue:
        return ""
    
    comments = issue.get("comments", [])
    # Extract comments that look like review/QA/dispatch content
    relevant = []
    for c in comments:
        body = c.get("body", "")
        # Skip short comments
        if len(body) > 50:
            relevant.append(body[:2000])  # Cap per comment
    
    return "\n---\n".join(relevant[:10])  # Cap total comments


def extract_acceptance_tests(text: str, limit: int = 6) -> list[str]:
    """Pull named acceptance tests or checkbox requirements from a ticket body."""
    if not text:
        return []
    matches = re.findall(r"`(test_[^`]+)`", text)
    if matches:
        return matches[:limit]

    lines = []
    capture = False
    for raw in text.splitlines():
        line = raw.strip()
        lower = line.lower()
        if "acceptance test" in lower:
            capture = True
            continue
        if capture and (line.startswith("##") or line.startswith("###")):
            break
        if capture and line.startswith(("- ", "* ")):
            lines.append(line[2:].strip())
        elif capture and line.startswith("`test_"):
            lines.append(line.strip("`"))
    return lines[:limit]


def summarize_acceptance_tests(text: str) -> str:
    tests = extract_acceptance_tests(text)
    if tests:
        return "\n".join(f"- {t}" for t in tests)
    return "[No named acceptance tests found]"


def infer_engineer_role(record: dict, title: str, body: str) -> str:
    role = str(record.get("engineer_role") or "").strip().lower()
    if role:
        return role
    hay = f"{title}\n{body}".lower()
    if any(tok in hay for tok in ["ui", "frontend", "streamlit", "billing page", "auth page", "copy"]):
        return "frontend"
    if any(tok in hay for tok in ["api", "database", "backend", "importer", "pipeline", "webhook"]):
        return "backend"
    return "fullstack"


def infer_priority(labels: list[str], title: str, body: str) -> str:
    label_set = {l.lower() for l in labels}
    if any("priority:high" == l or "p0" in l or "critical" in l for l in label_set):
        return "critical"
    if any("priority:medium" == l or "high" == l for l in label_set):
        return "high"
    hay = f"{title}\n{body}".lower()
    if any(tok in hay for tok in ["launch", "critical", "urgent", "blocker", "severity: 🔴"]):
        return "critical"
    return "normal"


def summarize_issue_comments(repo: str, ticket_num: str, keywords: list[str], limit: int = 2) -> list[str]:
    issue = fetch_issue(repo, ticket_num)
    if not issue:
        return []
    out = []
    for c in issue.get("comments", []):
        body = c.get("body", "")
        low = body.lower()
        if any(k in low for k in keywords):
            out.append(body[:1800])
        if len(out) >= limit:
            break
    return out


def mine_code_review_rejections(issue: dict, repo: str, ticket_num: str, record: dict, base_inputs: dict) -> list[dict]:
    """Create additional reject/request-changes review examples from issue comments."""
    examples = []
    for c in issue.get("comments", []):
        body = c.get("body", "")
        low = body.lower()
        if not any(tok in low for tok in ["verdict:** request changes", "verdict: request changes", "review rejected", "scope violation", "request changes"]):
            continue
        findings_lines = []
        for line in body.splitlines():
            s = line.strip()
            if s.startswith(("- ", "* ", "1. ", "2. ", "3. ")):
                findings_lines.append(s)
            if len(findings_lines) >= 6:
                break
        scope = "FAIL" if "scope violation" in low else "PASS"
        example = {
            **base_inputs,
            "verdict": "REJECT",
            "findings": "\n".join(findings_lines) if findings_lines else body[:600],
            "scope_check": scope,
            "review_comment": body[:2500],
            "_repo": repo,
            "_ticket": ticket_num,
            "_score": max(0.35, min(0.8, float(record.get("calculated_score", 0.5) or 0.5))),
            "_label": "reject-mined",
        }
        examples.append(example)
    return examples


def build_code_review_example(record: dict) -> list[dict] | None:
    """Build a CodeReviewSignature training example from a quality record."""
    repo = normalize_repo(record.get("repo", ""))
    ticket_num = normalize_ticket(record.get("ticket", ""))
    if not repo or not ticket_num:
        return None

    issue = fetch_issue(repo, ticket_num)
    if not issue:
        return None

    ticket_body = issue.get("body", "") or ""
    if not ticket_body.strip():
        return None

    dspy_inputs = record.get("dspy_inputs") or {}
    # Get review comments as fallback only — historical issue threads often contain
    # triage/dispatch noise that should not be preferred over stage-specific fields.
    comments = fetch_issue_comments_text(repo, ticket_num)

    findings = dspy_inputs.get("findings") or f"Findings count: {record.get('findings_count', 0)}, Actionable: {record.get('actionable_findings', 0)}"
    review_comment = (
        dspy_inputs.get("review_comment")
        or record.get("review_comment")
        or record.get("notes")
        or comments[:2000]
    )

    base_inputs = {
        "ticket_body": (dspy_inputs.get("ticket_body") or ticket_body)[:4000],
        "diff": dspy_inputs.get("diff") or f"[Historical - ticket {repo}#{ticket_num}]",
        "conventions": dspy_inputs.get("conventions") or "[Standard project conventions]",
        "lint_output": dspy_inputs.get("lint_output") or "",
        "streamlit_gotchas": dspy_inputs.get("streamlit_gotchas") or ("[Standard Streamlit gotchas]" if "churn_copilot" in repo or "streamlit" in repo.lower() else ""),
    }

    examples = [{
        **base_inputs,
        "verdict": record.get("verdict", "APPROVE"),
        "findings": findings,
        "scope_check": "FAIL" if record.get("scope_violation_flagged") else "PASS",
        "review_comment": review_comment,
        "_repo": repo,
        "_ticket": ticket_num,
        "_score": record.get("calculated_score", 0),
        "_label": record.get("label", ""),
    }]

    examples.extend(mine_code_review_rejections(issue, repo, ticket_num, record, base_inputs))
    return examples


def build_engineer_example(record: dict) -> dict | None:
    """Build an EngineerSignature training example."""
    repo = normalize_repo(record.get("repo", ""))
    ticket_num = normalize_ticket(record.get("ticket", ""))
    if not repo or not ticket_num:
        return None

    issue = fetch_issue(repo, ticket_num)
    if not issue:
        return None

    ticket_body = issue.get("body", "") or ""
    if not ticket_body.strip():
        return None

    issue_comments = summarize_issue_comments(repo, ticket_num, ["implemented", "what changed", "commit", "tests", "local verification"], limit=3)
    dspy_inputs = record.get("dspy_inputs") or {}
    title = issue.get("title", "") or record.get("ticket_title", "")
    role = infer_engineer_role(record, title, ticket_body)
    tests = dspy_inputs.get("tests") or summarize_acceptance_tests(ticket_body)
    code_changes = dspy_inputs.get("code_changes") or "\n---\n".join(issue_comments) or (record.get("notes") or f"Implemented ticket #{ticket_num} in scoped files")
    impl_plan = dspy_inputs.get("implementation_plan") or f"Implement #{ticket_num}: {title}" or f"Implement ticket #{ticket_num}"
    commit_message = dspy_inputs.get("commit_message") or f"fix(#{ticket_num}): {title[:60]}"

    return {
        "ticket_body": ticket_body[:4000],
        "codebase_context": dspy_inputs.get("codebase_context") or f"[{repo} codebase]",
        "conventions": dspy_inputs.get("conventions") or "[Standard project conventions]",
        "streamlit_gotchas": dspy_inputs.get("streamlit_gotchas") or ("[Standard Streamlit gotchas]" if "churn_copilot" in repo else ""),
        "engineer_role": dspy_inputs.get("engineer_role") or role,
        # Outputs
        "implementation_plan": impl_plan,
        "code_changes": code_changes,
        "tests": tests,
        "commit_message": commit_message,
        # Meta
        "_repo": repo,
        "_ticket": ticket_num,
        "_score": record.get("calculated_score", 0),
        "_label": record.get("label", ""),
    }


def build_qa_example(record: dict) -> dict | None:
    """Build a QASignature training example."""
    repo = normalize_repo(record.get("repo", ""))
    ticket_num = normalize_ticket(record.get("ticket", ""))
    if not repo or not ticket_num:
        return None

    issue = fetch_issue(repo, ticket_num)
    if not issue:
        return None

    ticket_body = issue.get("body", "") or ""
    if not ticket_body.strip():
        return None

    dspy_inputs = record.get("dspy_inputs") or {}
    qa_comments = summarize_issue_comments(repo, ticket_num, ["qa", "verified", "experiment", "merged", "pass", "fail", "bug"], limit=3)
    bug_count = int(record.get("real_bugs_found") or 0) + int(record.get("regressions_found") or 0)
    if dspy_inputs.get("qa_verdict"):
        qa_verdict = str(dspy_inputs.get("qa_verdict")).upper()
    else:
        qa_verdict = "FAIL" if bug_count > 0 else "PASS"
    merge_safe = dspy_inputs.get("merge_safe") or ("NO" if bug_count > 0 else "YES")
    verification_report = dspy_inputs.get("verification_report") or record.get("notes") or "\n---\n".join(qa_comments) or f"QA verification for ticket #{ticket_num}"
    bugs_found = dspy_inputs.get("bugs_found")
    if not bugs_found:
        bugs_found = "No bugs found during QA verification." if bug_count == 0 else f"Found {bug_count} real bug/regression issue(s) during QA verification."

    return {
        "ticket_body": dspy_inputs.get("ticket_body") or ticket_body[:4000],
        "code_review_comment": dspy_inputs.get("code_review_comment") or record.get("review_comment") or record.get("notes", ""),
        "diff": dspy_inputs.get("diff") or f"[Historical - ticket {repo}#{ticket_num}]",
        "test_output": dspy_inputs.get("test_output") or record.get("notes") or "[Historical test output unavailable]",
        # Outputs
        "merge_safe": merge_safe,
        "verification_report": verification_report,
        "bugs_found": bugs_found,
        "qa_verdict": qa_verdict,
        # Meta
        "_repo": repo,
        "_ticket": ticket_num,
        "_score": record.get("calculated_score", 0),
        "_label": record.get("label", ""),
    }


def build_triage_example(record: dict) -> dict | None:
    """Build a TriageSignature training example."""
    repo = normalize_repo(record.get("repo", ""))
    ticket_num = normalize_ticket(record.get("ticket", ""))
    if not repo or not ticket_num:
        return None

    issue = fetch_issue(repo, ticket_num)
    if not issue:
        return None

    ticket_body = issue.get("body", "") or ""
    if not ticket_body.strip():
        return None

    labels = [l.get("name", "") for l in issue.get("labels", [])]
    dspy_inputs = record.get("dspy_inputs") or {}
    title = issue.get("title", "") or record.get("ticket_title", "")
    role = dspy_inputs.get("engineer_role") or infer_engineer_role(record, title, ticket_body)
    acceptance_tests = dspy_inputs.get("acceptance_tests") or summarize_acceptance_tests(ticket_body)
    dispatch_note = dspy_inputs.get("dispatch_note") or record.get("notes") or f"Triage #{ticket_num}: {title}"
    priority = dspy_inputs.get("priority_assessment") or infer_priority(labels, title, ticket_body)

    return {
        "ticket_body": ticket_body[:4000],
        "ticket_labels": ", ".join(labels),
        "evolver_matches": "",
        "dependency_status": "all closed",
        "project_type": "streamlit" if "churn_copilot" in repo else "cli",
        # Outputs
        "acceptance_tests": acceptance_tests,
        "engineer_role": role,
        "dispatch_note": dispatch_note,
        "priority_assessment": priority,
        # Meta
        "_repo": repo,
        "_ticket": ticket_num,
        "_score": record.get("calculated_score", 0),
        "_label": record.get("label", ""),
    }


STAGE_BUILDERS = {
    "code-review": build_code_review_example,
    "engineer": build_engineer_example,
    "qa": build_qa_example,
    "triage": build_triage_example,
}


def reconstruct_stage(stage: str, dry_run: bool = False):
    """Reconstruct training data for one stage."""
    jsonl_file = METRICS_DIR / STAGE_FILES[stage]
    builder = STAGE_BUILDERS[stage]

    if not jsonl_file.exists():
        print(f"SKIP: {jsonl_file} not found")
        return

    records = []
    with open(jsonl_file) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    print(f"\n{'='*60}")
    print(f"Stage: {stage} | Source: {jsonl_file.name} | Records: {len(records)}")
    print(f"{'='*60}")

    examples = []
    skipped = 0
    errors = 0

    for i, record in enumerate(records):
        score = record.get("calculated_score", 0)
        if score < 0.3:
            skipped += 1
            continue

        if dry_run:
            repo = normalize_repo(record.get("repo", ""))
            ticket = normalize_ticket(record.get("ticket", ""))
            print(f"  Would fetch: {repo}#{ticket} (score={score:.2f})")
            continue

        example = builder(record)
        if isinstance(example, list):
            examples.extend(example)
            ex = example[0]
            print(f"  ✅ {ex['_repo']}#{ex['_ticket']} (+{len(example)-1} mined) (score={ex['_score']:.2f})")
        elif example:
            examples.append(example)
            print(f"  ✅ {example['_repo']}#{example['_ticket']} (score={example['_score']:.2f})")
        else:
            errors += 1
            print(f"  ❌ Could not reconstruct: {record.get('repo')}#{record.get('ticket')}")

        # Rate limit: gh CLI is fast but let's be polite
        if (i + 1) % 10 == 0:
            time.sleep(0.5)

    if dry_run:
        print(f"\nDry run: {len(records) - skipped} would be fetched, {skipped} below threshold")
        return

    # Write enriched training data
    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / f"{stage}-training.jsonl"
    with open(output_path, "w") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\nResults: {len(examples)} enriched, {skipped} below threshold, {errors} failed")
    print(f"Written to: {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Reconstruct DSPy training data from GitHub")
    parser.add_argument("--stage", default="all", choices=["all"] + list(STAGE_FILES.keys()))
    parser.add_argument("--dry-run", action="store_true", help="Don't fetch, just show what would be done")
    args = parser.parse_args()

    stages = list(STAGE_FILES.keys()) if args.stage == "all" else [args.stage]

    for stage in stages:
        reconstruct_stage(stage, dry_run=args.dry_run)

    if not args.dry_run:
        print(f"\n{'='*60}")
        print("Done! Training data written to framework/dspy/training-data/")
        print("Next: update compile.py to read from training-data/ instead of metrics/")


if __name__ == "__main__":
    main()
