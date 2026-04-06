#!/usr/bin/env python3
"""DSPy Shadow Evaluation — Run current + optimized prompts side-by-side.

Usage:
    python shadow-eval.py --stage code-review --ticket-data ticket.json

Runs both the current (baseline) prompt and the DSPy-optimized prompt on the
same input, logs both outputs and the eventual human label to shadow-log.jsonl.

This does NOT replace the production prompt — it only collects comparison data.
When the optimized prompt consistently beats the baseline, we promote it.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import dspy
except ImportError:
    print("ERROR: DSPy not installed. Run: pip install dspy-ai")
    sys.exit(1)

from signatures import (
    CodeReviewSignature,
    EngineerSignature,
    QASignature,
    TriageSignature,
)

PROGRAMS_DIR = Path(__file__).parent / "programs"
SHADOW_LOG = Path(__file__).parent / "shadow-log.jsonl"

STAGE_CONFIG = {
    "code-review": {
        "signature": CodeReviewSignature,
        "program_file": "code-review-optimized.json",
    },
    "engineer": {
        "signature": EngineerSignature,
        "program_file": "engineer-optimized.json",
    },
    "qa": {
        "signature": QASignature,
        "program_file": "qa-optimized.json",
    },
    "triage": {
        "signature": TriageSignature,
        "program_file": "triage-optimized.json",
    },
}


def run_shadow(stage: str, ticket_data: dict, model: str = "anthropic/claude-sonnet-4-6"):
    """Run both baseline and optimized prompts, log comparison."""
    config = STAGE_CONFIG[stage]
    program_path = PROGRAMS_DIR / config["program_file"]

    if not program_path.exists():
        print(f"ERROR: No compiled program at {program_path}. Run compile.py first.")
        sys.exit(1)

    # Configure LM
    lm = dspy.LM(model)
    dspy.configure(lm=lm)

    # Baseline: unoptimized prompt
    baseline = dspy.Predict(config["signature"])
    baseline_result = baseline(**ticket_data)

    # Optimized: DSPy-compiled prompt
    optimized = dspy.Predict(config["signature"])
    optimized.load(str(program_path))
    optimized_result = optimized(**ticket_data)

    # Log both results
    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "ticket": ticket_data.get("ticket", "unknown"),
        "baseline": {
            "verdict": getattr(baseline_result, "verdict", None),
            "findings": getattr(baseline_result, "findings", None),
        },
        "optimized": {
            "verdict": getattr(optimized_result, "verdict", None),
            "findings": getattr(optimized_result, "findings", None),
        },
        "human_label": None,  # Filled in later when ticket closes
        "human_score": None,
    }

    with open(SHADOW_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

    print(f"Shadow logged: {stage} for {ticket_data.get('ticket', '?')}")
    print(f"  Baseline verdict: {log_entry['baseline']['verdict']}")
    print(f"  Optimized verdict: {log_entry['optimized']['verdict']}")

    return log_entry


def analyze_shadow_log():
    """Analyze shadow-log.jsonl to compare baseline vs optimized performance."""
    if not SHADOW_LOG.exists():
        print("No shadow log yet.")
        return

    entries = []
    with open(SHADOW_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    labeled = [e for e in entries if e.get("human_score") is not None]
    print(f"Total shadow entries: {len(entries)}")
    print(f"Labeled (with human score): {len(labeled)}")

    if not labeled:
        print("No labeled entries yet. Labels are added when tickets close.")
        return

    # Compare
    baseline_wins = 0
    optimized_wins = 0
    ties = 0

    for entry in labeled:
        b_verdict = entry["baseline"].get("verdict", "").upper()
        o_verdict = entry["optimized"].get("verdict", "").upper()
        human = entry.get("human_label", "").upper()

        if b_verdict == human and o_verdict != human:
            baseline_wins += 1
        elif o_verdict == human and b_verdict != human:
            optimized_wins += 1
        else:
            ties += 1

    print(f"\nResults:")
    print(f"  Baseline wins:  {baseline_wins}")
    print(f"  Optimized wins: {optimized_wins}")
    print(f"  Ties:           {ties}")

    if optimized_wins > baseline_wins and len(labeled) >= 20:
        print("\n🎯 PROMOTION CANDIDATE: Optimized prompt beats baseline on 20+ examples!")
    elif len(labeled) < 20:
        print(f"\n⏳ Need {20 - len(labeled)} more labeled entries before promotion decision.")


def main():
    parser = argparse.ArgumentParser(description="DSPy Shadow Evaluation")
    parser.add_argument("--stage", choices=STAGE_CONFIG.keys())
    parser.add_argument("--ticket-data", help="JSON file with ticket inputs")
    parser.add_argument("--analyze", action="store_true", help="Analyze shadow log")
    parser.add_argument("--model", default="anthropic/claude-sonnet-4-6")
    args = parser.parse_args()

    if args.analyze:
        analyze_shadow_log()
    elif args.stage and args.ticket_data:
        with open(args.ticket_data) as f:
            ticket_data = json.load(f)
        run_shadow(args.stage, ticket_data, args.model)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
