#!/usr/bin/env python3
"""Shadow evaluation runner for the board review pipeline.

Called during Phase 4 (ticket closure) to run both baseline and optimized prompts
on the same ticket inputs, logging the comparison for later analysis.

Usage:
    python shadow-run.py --stage code-review --repo owner/repo --ticket 123
    python shadow-run.py --stage all --repo owner/repo --ticket 123
    python shadow-run.py --analyze  # Show win/loss stats

Exit codes:
    0 = success (shadow logged)
    1 = error (missing args, API failure, etc.)
    2 = skipped (no compiled program for this stage)
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import dspy
except ImportError:
    print("ERROR: DSPy not installed. Run: pip install dspy-ai", file=sys.stderr)
    sys.exit(1)

# Add parent to path for signature imports
sys.path.insert(0, str(Path(__file__).parent))
from signatures import (
    CodeReviewSignature,
    EngineerSignature,
    QASignature,
    TriageSignature,
)

PROGRAMS_DIR = Path(__file__).parent / "programs"
SHADOW_LOG = Path(__file__).parent / "shadow-log.jsonl"
METRICS_DIR = Path(__file__).parent.parent / "metrics"

STAGE_METRIC_FILES = {
    "code-review": "review-quality.jsonl",
    "engineer": "engineer-quality.jsonl",
    "qa": "qa-quality.jsonl",
    "triage": "triage-quality.jsonl",
}

REPO_ALIASES = {
    "churn_copilot_hendrix": "hendrixAIDev/churn_copilot_hendrix",
    "character-life-sim": "hendrixAIDev/character-life-sim",
    "openclaw-assistant": "zrjaa1/openclaw-assistant",
    "hendrixAIDev": "hendrixAIDev/hendrixAIDev",
    "hendrixaidev.github.io": "hendrixAIDev/hendrixaidev.github.io",
    "cp": "hendrixAIDev/churn_copilot_hendrix",
    "churn": "hendrixAIDev/churn_copilot_hendrix",
    "clse": "hendrixAIDev/character-life-sim",
    "hx": "hendrixAIDev/hendrixAIDev",
    "oca": "zrjaa1/openclaw-assistant",
}

STAGE_CONFIG = {
    "code-review": {
        "signature": CodeReviewSignature,
        "program_file": "code-review-optimized.json",
        "output_fields": ["verdict", "findings", "scope_check", "review_comment"],
    },
    "engineer": {
        "signature": EngineerSignature,
        "program_file": "engineer-optimized.json",
        "output_fields": ["implementation_plan", "code_changes", "tests", "commit_message"],
    },
    "qa": {
        "signature": QASignature,
        "program_file": "qa-optimized.json",
        "output_fields": ["merge_safe", "verification_report", "bugs_found", "qa_verdict"],
    },
    "triage": {
        "signature": TriageSignature,
        "program_file": "triage-optimized.json",
        "output_fields": ["acceptance_tests", "engineer_role", "dispatch_note", "priority_assessment"],
    },
}


def normalize_repo_ticket(repo: str | None, ticket: str | None, trace_id: str | None = None) -> tuple[str, str]:
    """Normalize repo/ticket identifiers across shadow + metrics files."""
    repo = str(repo or "").strip()
    ticket = str(ticket or "").strip()
    trace_id = str(trace_id or "").strip()

    full_repo = repo if "/" in repo else REPO_ALIASES.get(repo, repo)

    if (not full_repo or "/" not in full_repo) and trace_id and "#" in trace_id:
        prefix, suffix = trace_id.split("#", 1)
        full_repo = REPO_ALIASES.get(prefix, full_repo)
        if not ticket:
            ticket = f"#{suffix}"

    m = re.search(r"(\d+)", ticket or trace_id)
    ticket_num = m.group(1) if m else ""
    return full_repo, ticket_num


def normalize_score(record: dict) -> float | None:
    """Return a 0-1 human score from metric records with mixed schemas."""
    score = record.get("calculated_score", record.get("score"))
    if score is None:
        return None
    try:
        score = float(score)
    except (TypeError, ValueError):
        return None
    if score > 1.0:
        score = score / 10.0
    return max(0.0, min(1.0, round(score, 2)))


def normalize_quality_label(record: dict, score: float | None) -> str | None:
    label = record.get("label")
    if isinstance(label, str) and label.strip():
        return label.strip().lower()
    if score is None:
        return None
    if score >= 0.85:
        return "good"
    if score >= 0.60:
        return "acceptable"
    return "poor"


def truthy_bug_count(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    text = str(value).strip().lower()
    return text not in {"", "0", "none", "(none)", "no", "false", "pass", "n/a"}


def normalize_verdict(value: str | None) -> str:
    text = str(value or "").upper()
    if "REQUEST CHANGE" in text or text == "REJECT":
        return "REJECT"
    if text.startswith("FAIL") or text.startswith("NO"):
        return "FAIL"
    if text.startswith("PASS") or text.startswith("YES"):
        return "PASS"
    if text.startswith("APPROVE"):
        return "APPROVE"
    return text


def normalize_role(value: str | None) -> str:
    text = str(value or "").strip().lower().replace("_", "-")
    if not text:
        return ""
    if "front" in text:
        return "frontend"
    if "back" in text:
        return "backend"
    if "content" in text:
        return "content"
    if "fullstack" in text or text == "fullstack-engineer":
        return "fullstack"
    if text == "cli":
        return "cli"
    return text


def normalize_boolish(value) -> str:
    if isinstance(value, bool):
        return "YES" if value else "NO"
    text = str(value or "").strip().lower()
    if text in {"yes", "true", "pass", "passed", "safe", "ok"}:
        return "YES"
    if text in {"no", "false", "fail", "failed", "unsafe"}:
        return "NO"
    return ""


def contains_named_tests(text: str | None) -> bool:
    text = str(text or "")
    return "test_" in text or "pytest" in text.lower()


def looks_like_placeholder(text: str | None) -> bool:
    text = str(text or "").strip()
    lowered = text.lower()
    return (
        not text
        or lowered.startswith("[historical")
        or lowered.startswith("[reconstructed")
        or lowered.startswith("[tests")
        or "dispatching:" in lowered
        or "cto triage" in lowered
    )


def safe_commit_message(text: str | None) -> str:
    text = str(text or "").strip().lower()
    if not text:
        return "NO"
    banned = ("fix #", "fixes #", "fixed #", "close #", "closes #", "closed #", "resolve #", "resolves #", "resolved #")
    return "NO" if any(tok in text for tok in banned) else "YES"


def engineer_signal_score(output: dict) -> float:
    parts = []
    plan = output.get("implementation_plan", "")
    code_changes = output.get("code_changes", "")
    tests = output.get("tests", "")
    commit_message = output.get("commit_message", "")
    parts.append(0.0 if looks_like_placeholder(plan) else 1.0)
    parts.append(0.0 if looks_like_placeholder(code_changes) else 1.0)
    parts.append(1.0 if contains_named_tests(tests) else 0.0)
    parts.append(1.0 if safe_commit_message(commit_message) == "YES" else 0.0)
    return round(sum(parts) / len(parts), 2)


def triage_signal_score(output: dict) -> float:
    parts = []
    acceptance_tests = output.get("acceptance_tests", "")
    engineer_role = normalize_role(output.get("engineer_role"))
    dispatch_note = output.get("dispatch_note", "")
    priority = str(output.get("priority_assessment", "")).strip().lower()
    parts.append(1.0 if contains_named_tests(acceptance_tests) else 0.0)
    parts.append(1.0 if engineer_role in {"frontend", "backend", "fullstack", "content", "cli"} else 0.0)
    parts.append(0.0 if looks_like_placeholder(dispatch_note) else 1.0)
    parts.append(1.0 if any(tok in priority for tok in ["critical", "high", "medium", "low", "normal"]) else 0.0)
    return round(sum(parts) / len(parts), 2)


def derive_human_targets(stage: str, record: dict, quality_label: str | None) -> dict:
    """Attach stage-specific human targets for later analysis."""
    out: dict[str, str] = {}

    if stage == "code-review":
        verdict = record.get("verdict")
        if verdict:
            out["human_target_verdict"] = normalize_verdict(verdict)
        elif quality_label in {"poor", "failed"}:
            out["human_target_verdict"] = "REJECT"
        elif quality_label:
            out["human_target_verdict"] = "APPROVE"

    elif stage == "qa":
        bugs_found = any(
            truthy_bug_count(record.get(k))
            for k in ("real_bugs_found", "regressions_found", "bugs_found")
        )
        out["human_target_verdict"] = "FAIL" if bugs_found else "PASS"
        out["human_target_merge_safe"] = "NO" if bugs_found else "YES"

    elif stage == "triage":
        preferred_role = (
            record.get("correct_role")
            if isinstance(record.get("correct_role"), str)
            else record.get("engineer_role")
            or record.get("role_dispatched")
            or record.get("dispatched_role")
        )
        role = normalize_role(preferred_role)
        if role:
            out["human_target_engineer_role"] = role
        out["human_target_acceptance_tests"] = "YES" if record.get("acceptance_tests_added") else "NO"

    elif stage == "engineer":
        out["human_target_tests"] = "YES" if (record.get("tests_match_acceptance_criteria") or record.get("tests_included")) else "NO"
        out["human_target_scope"] = "YES" if record.get("scope_respected") else "NO"
        out["human_target_local_testing"] = "YES" if record.get("local_testing_documented") else "NO"
        out["human_target_safe_commit"] = "YES"

    return out


def load_metric_index(stage: str) -> dict[tuple[str, str], dict]:
    """Load a metric file indexed by normalized repo/ticket."""
    metric_file = METRICS_DIR / STAGE_METRIC_FILES[stage]
    index: dict[tuple[str, str], dict] = {}
    if not metric_file.exists():
        return index

    with open(metric_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            key = normalize_repo_ticket(
                record.get("repo"),
                record.get("ticket") or record.get("issue"),
                record.get("trace_id"),
            )
            if key[0] and key[1]:
                index[key] = record
    return index


def backfill_labels() -> tuple[int, int]:
    """Backfill shadow human labels/scores from stage-specific metric files."""
    if not SHADOW_LOG.exists():
        print("No shadow log yet.")
        return 0, 0

    entries = []
    with open(SHADOW_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    metric_indexes = {stage: load_metric_index(stage) for stage in STAGE_CONFIG}
    updated = 0
    matched = 0

    for entry in entries:
        stage = entry.get("stage")
        if stage not in metric_indexes:
            continue
        key = normalize_repo_ticket(entry.get("repo"), entry.get("ticket"))
        record = metric_indexes[stage].get(key)
        if not record:
            continue
        matched += 1

        score = normalize_score(record)
        label = normalize_quality_label(record, score)
        targets = derive_human_targets(stage, record, label)

        changed = False
        for field, value in {
            "human_label": label,
            "human_score": score,
            "human_source": STAGE_METRIC_FILES[stage],
            **targets,
        }.items():
            if value is not None and entry.get(field) != value:
                entry[field] = value
                changed = True

        if changed:
            updated += 1

    if updated:
        with open(SHADOW_LOG, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    return updated, matched


def fetch_ticket_body(repo: str, ticket: str) -> str:
    """Fetch ticket body from GitHub."""
    result = subprocess.run(
        ["gh", "issue", "view", ticket, "--repo", repo, "--json", "body,title,labels"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return ""
    data = json.loads(result.stdout)
    return data.get("body", "") or ""


def fetch_ticket_comments(repo: str, ticket: str) -> list[str]:
    """Fetch ticket comments for context."""
    result = subprocess.run(
        ["gh", "issue", "view", ticket, "--repo", repo, "--json", "comments"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return []
    data = json.loads(result.stdout)
    return [c.get("body", "")[:2000] for c in data.get("comments", []) if len(c.get("body", "")) > 50]


def build_inputs(stage: str, repo: str, ticket: str) -> dict:
    """Build signature-specific inputs from GitHub data."""
    body = fetch_ticket_body(repo, ticket)
    if not body:
        return {}

    comments = fetch_ticket_comments(repo, ticket)
    is_streamlit = "churn_copilot" in repo or "streamlit" in repo.lower()

    # Load conventions if available
    conv_path = Path(__file__).parent.parent / "roles" / "CONVENTIONS.md"
    conventions = conv_path.read_text()[:2000] if conv_path.exists() else "[Standard conventions]"

    # Load streamlit gotchas if applicable
    gotchas_path = Path(__file__).parent.parent / "knowledge" / "streamlit-gotchas.md"
    gotchas = gotchas_path.read_text()[:2000] if (is_streamlit and gotchas_path.exists()) else ""

    # Extract diff/lint from comments if present
    diff_text = "[See ticket comments]"
    lint_text = ""
    for c in comments:
        if "diff" in c.lower() or "files changed" in c.lower() or "```diff" in c.lower():
            diff_text = c[:3000]
            break
    for c in comments:
        if "ruff" in c.lower() or "lint" in c.lower() or "all checks passed" in c.lower():
            lint_text = c[:500]
            break

    if stage == "code-review":
        return {
            "ticket_body": body[:4000],
            "diff": diff_text,
            "conventions": conventions,
            "lint_output": lint_text,
            "streamlit_gotchas": gotchas,
        }
    elif stage == "engineer":
        return {
            "ticket_body": body[:4000],
            "codebase_context": f"[{repo} codebase]",
            "conventions": conventions,
            "streamlit_gotchas": gotchas,
            "engineer_role": "fullstack",
        }
    elif stage == "qa":
        return {
            "ticket_body": body[:4000],
            "code_review_comment": comments[0] if comments else "Approved",
            "diff": diff_text,
            "test_output": "[See ticket comments for test results]",
        }
    elif stage == "triage":
        return {
            "ticket_body": body[:4000],
            "ticket_labels": "",  # Could fetch from GitHub
            "evolver_matches": "",
            "dependency_status": "all closed",
            "project_type": "streamlit" if is_streamlit else "cli",
        }
    return {}


def run_shadow(stage: str, repo: str, ticket: str, model: str) -> dict | None:
    """Run shadow comparison for one stage."""
    config = STAGE_CONFIG[stage]
    program_path = PROGRAMS_DIR / config["program_file"]

    if not program_path.exists():
        print(f"SKIP: No compiled program for {stage} at {program_path}")
        return None

    inputs = build_inputs(stage, repo, ticket)
    if not inputs:
        print(f"SKIP: Could not build inputs for {repo}#{ticket}")
        return None

    # Configure LM
    lm = dspy.LM(model)
    dspy.configure(lm=lm)

    # Run baseline (no demos)
    print(f"  Running baseline {stage}...", end=" ", flush=True)
    t0 = time.time()
    baseline = dspy.Predict(config["signature"])
    try:
        result_b = baseline(**inputs)
        baseline_out = {f: getattr(result_b, f, "")[:500] for f in config["output_fields"]}
    except Exception as e:
        baseline_out = {"error": str(e)[:200]}
    t_baseline = time.time() - t0
    print(f"({t_baseline:.1f}s)")

    # Run optimized (with demos)
    print(f"  Running optimized {stage}...", end=" ", flush=True)
    t0 = time.time()
    optimized = dspy.Predict(config["signature"])
    optimized.load(str(program_path))
    try:
        result_o = optimized(**inputs)
        optimized_out = {f: getattr(result_o, f, "")[:500] for f in config["output_fields"]}
    except Exception as e:
        optimized_out = {"error": str(e)[:200]}
    t_optimized = time.time() - t0
    print(f"({t_optimized:.1f}s)")

    # Build log entry
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "repo": repo,
        "ticket": f"#{ticket}",
        "model": model,
        "baseline": baseline_out,
        "optimized": optimized_out,
        "latency": {"baseline_s": round(t_baseline, 1), "optimized_s": round(t_optimized, 1)},
        "human_label": None,  # Filled in later by Phase 4 metrics recording
        "human_score": None,
    }

    # Append to shadow log
    with open(SHADOW_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def analyze():
    """Analyze shadow log for win/loss stats."""
    if not SHADOW_LOG.exists():
        print("No shadow log yet.")
        return

    entries = []
    with open(SHADOW_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    total = len(entries)
    labeled = [e for e in entries if e.get("human_score") is not None]
    by_stage = {}
    for e in entries:
        s = e.get("stage", "?")
        by_stage.setdefault(s, []).append(e)

    print(f"Shadow Log Summary")
    print(f"{'='*50}")
    print(f"Total entries: {total}")
    print(f"Labeled (with human score): {len(labeled)}")
    print()

    for stage, stage_entries in sorted(by_stage.items()):
        print(f"  {stage}: {len(stage_entries)} entries")
        stage_labeled = [e for e in stage_entries if e.get("human_score") is not None]
        if stage_labeled:
            baseline_wins = 0
            optimized_wins = 0
            ties = 0
            comparable = 0
            for e in stage_labeled:
                if stage == "code-review":
                    human = normalize_verdict(e.get("human_target_verdict"))
                    b_value = normalize_verdict(e.get("baseline", {}).get("verdict"))
                    o_value = normalize_verdict(e.get("optimized", {}).get("verdict"))
                elif stage == "qa":
                    human = normalize_verdict(e.get("human_target_verdict"))
                    b_value = normalize_verdict(
                        e.get("baseline", {}).get("qa_verdict") or e.get("baseline", {}).get("merge_safe")
                    )
                    o_value = normalize_verdict(
                        e.get("optimized", {}).get("qa_verdict") or e.get("optimized", {}).get("merge_safe")
                    )
                elif stage == "triage":
                    b_score = 0
                    o_score = 0
                    dimensions = 0
                    human_role = normalize_role(e.get("human_target_engineer_role"))
                    if human_role:
                        dimensions += 1
                        if normalize_role(e.get("baseline", {}).get("engineer_role")) == human_role:
                            b_score += 1
                        if normalize_role(e.get("optimized", {}).get("engineer_role")) == human_role:
                            o_score += 1
                    human_tests = normalize_boolish(e.get("human_target_acceptance_tests"))
                    if human_tests:
                        dimensions += 1
                        if normalize_boolish(contains_named_tests(e.get("baseline", {}).get("acceptance_tests"))) == human_tests:
                            b_score += 1
                        if normalize_boolish(contains_named_tests(e.get("optimized", {}).get("acceptance_tests"))) == human_tests:
                            o_score += 1
                    if not dimensions:
                        continue
                    comparable += 1
                    if b_score > o_score:
                        baseline_wins += 1
                    elif o_score > b_score:
                        optimized_wins += 1
                    else:
                        ties += 1
                    continue
                elif stage == "engineer":
                    dimensions = 0
                    b_score = 0
                    o_score = 0
                    target_tests = normalize_boolish(e.get("human_target_tests"))
                    if target_tests:
                        dimensions += 1
                        if normalize_boolish(contains_named_tests(e.get("baseline", {}).get("tests"))) == target_tests:
                            b_score += 1
                        if normalize_boolish(contains_named_tests(e.get("optimized", {}).get("tests"))) == target_tests:
                            o_score += 1
                    target_commit = normalize_boolish(e.get("human_target_safe_commit"))
                    if target_commit:
                        dimensions += 1
                        if safe_commit_message(e.get("baseline", {}).get("commit_message")) == target_commit:
                            b_score += 1
                        if safe_commit_message(e.get("optimized", {}).get("commit_message")) == target_commit:
                            o_score += 1
                    dimensions += 1
                    b_score += engineer_signal_score(e.get("baseline", {}))
                    o_score += engineer_signal_score(e.get("optimized", {}))
                    comparable += 1
                    if b_score > o_score:
                        baseline_wins += 1
                    elif o_score > b_score:
                        optimized_wins += 1
                    else:
                        ties += 1
                    continue
                else:
                    continue

                if not human:
                    continue

                comparable += 1
                if b_value == human and o_value != human:
                    baseline_wins += 1
                elif o_value == human and b_value != human:
                    optimized_wins += 1
                else:
                    ties += 1
            avg_score = sum(e.get("human_score", 0) for e in stage_labeled) / len(stage_labeled)
            print(f"    Avg human score: {avg_score:.2f}")
            if comparable:
                print(f"    Comparable labeled entries: {comparable}")
            print(f"    Baseline wins: {baseline_wins}")
            print(f"    Optimized wins: {optimized_wins}")
            print(f"    Ties: {ties}")
            if comparable >= 20 and optimized_wins >= max(3, baseline_wins + 2):
                print(f"    🎯 PROMOTION CANDIDATE!")
        else:
            print(f"    (no labels yet — add human_score to entries)")
    print()

    # Latency comparison
    b_times = [e["latency"]["baseline_s"] for e in entries if "latency" in e]
    o_times = [e["latency"]["optimized_s"] for e in entries if "latency" in e]
    if b_times:
        print(f"Avg latency — baseline: {sum(b_times)/len(b_times):.1f}s, optimized: {sum(o_times)/len(o_times):.1f}s")
        print(f"(Optimized is slower due to larger prompt with demos)")


def main():
    parser = argparse.ArgumentParser(description="DSPy Shadow Evaluation for Board Review")
    parser.add_argument("--stage", choices=list(STAGE_CONFIG.keys()) + ["all"])
    parser.add_argument("--repo", help="GitHub repo (owner/repo)")
    parser.add_argument("--ticket", help="Issue number")
    parser.add_argument("--model", default="openai/gpt-4.1-mini", help="LLM for evaluation")
    parser.add_argument("--analyze", action="store_true", help="Show shadow log stats")
    parser.add_argument("--backfill-labels", action="store_true", help="Backfill human labels/scores from metrics JSONL files")
    args = parser.parse_args()

    if args.backfill_labels:
        updated, matched = backfill_labels()
        print(f"Backfill complete: updated {updated} shadow entries from {matched} metric matches")
        return

    if args.analyze:
        analyze()
        return

    if not args.stage or not args.repo or not args.ticket:
        parser.error("--stage, --repo, and --ticket are required (or use --analyze)")

    stages = list(STAGE_CONFIG.keys()) if args.stage == "all" else [args.stage]

    print(f"Shadow evaluation: {args.repo}#{args.ticket}")
    print(f"Stages: {', '.join(stages)}")
    print()

    for stage in stages:
        print(f"[{stage}]")
        entry = run_shadow(stage, args.repo, args.ticket, args.model)
        if entry:
            # Quick summary
            b = entry["baseline"]
            o = entry["optimized"]
            print(f"  Baseline verdict: {b.get('verdict', b.get('qa_verdict', b.get('merge_safe', '?')))}")
            print(f"  Optimized verdict: {o.get('verdict', o.get('qa_verdict', o.get('merge_safe', '?')))}")
        print()

    print("✅ Shadow entries logged to framework/dspy/shadow-log.jsonl")


if __name__ == "__main__":
    main()
