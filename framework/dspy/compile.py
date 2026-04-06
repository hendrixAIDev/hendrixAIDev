#!/usr/bin/env python3
"""DSPy Compilation — Load labeled examples, optimize prompts, save programs.

Usage:
    python compile.py --stage code-review [--min-examples 50] [--output programs/]
    python compile.py --stage engineer --min-examples 30
    python compile.py --stage qa
    python compile.py --stage triage

Reads from framework/metrics/*.jsonl, compiles with DSPy BootstrapFewShot,
and saves optimized programs to programs/ directory.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import dspy
    from dspy.teleprompt import BootstrapFewShot
except ImportError:
    print("ERROR: DSPy not installed. Run: pip install dspy-ai")
    sys.exit(1)

from signatures import (
    CodeReviewSignature,
    EngineerSignature,
    QASignature,
    TriageSignature,
)

TRAINING_DIR = Path(__file__).parent / "training-data"
PROGRAMS_DIR = Path(__file__).parent / "programs"

STAGE_CONFIG = {
    "code-review": {
        "jsonl": "code-review-training.jsonl",
        "signature": CodeReviewSignature,
        "score_field": "_score",
        "min_score": 0.3,
    },
    "engineer": {
        "jsonl": "engineer-training.jsonl",
        "signature": EngineerSignature,
        "score_field": "_score",
        "min_score": 0.3,
    },
    "qa": {
        "jsonl": "qa-training.jsonl",
        "signature": QASignature,
        "score_field": "_score",
        "min_score": 0.3,
    },
    "triage": {
        "jsonl": "triage-training.jsonl",
        "signature": TriageSignature,
        "score_field": "_score",
        "min_score": 0.3,
    },
}


def load_examples(jsonl_path: Path, min_score: float, score_field: str = "_score") -> list[dict]:
    """Load labeled examples from JSONL, filtering by minimum score."""
    examples = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            score = record.get(score_field, 0)
            if score >= min_score:
                examples.append(record)
    return examples


def normalize_text(text) -> list[str]:
    text = str(text or "").lower()
    return re.findall(r"[a-z0-9_#./:-]+", text)


def overlap_score(a, b) -> float:
    a_tokens = set(normalize_text(a))
    b_tokens = set(normalize_text(b))
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def normalize_verdict(value) -> str:
    text = str(value or "").strip().upper()
    if "REQUEST CHANGE" in text or text == "REJECT":
        return "REJECT"
    if text.startswith("APPROVE"):
        return "APPROVE"
    if text.startswith("PASS"):
        return "PASS"
    if text.startswith("FAIL"):
        return "FAIL"
    if text.startswith("YES"):
        return "YES"
    if text.startswith("NO"):
        return "NO"
    return text


def normalize_role(value) -> str:
    text = str(value or "").strip().lower().replace("_", "-")
    if "front" in text:
        return "frontend"
    if "back" in text:
        return "backend"
    if "fullstack" in text:
        return "fullstack"
    if "content" in text:
        return "content"
    return text


def make_metric(stage: str, score_field: str):
    """Create a stage-aware DSPy metric that actually inspects predictions."""
    def metric(example, prediction, trace=None) -> float:
        base_quality = float(getattr(example, score_field, 0.0) or 0.0)

        if stage == "code-review":
            verdict_match = 1.0 if normalize_verdict(getattr(prediction, "verdict", "")) == normalize_verdict(getattr(example, "verdict", "")) else 0.0
            scope_match = 1.0 if normalize_verdict(getattr(prediction, "scope_check", "")) == normalize_verdict(getattr(example, "scope_check", "")) else 0.0
            findings_overlap = overlap_score(getattr(prediction, "findings", ""), getattr(example, "findings", ""))
            comment_overlap = overlap_score(getattr(prediction, "review_comment", ""), getattr(example, "review_comment", ""))
            behavior = (0.4 * verdict_match) + (0.2 * scope_match) + (0.2 * findings_overlap) + (0.2 * comment_overlap)
        elif stage == "engineer":
            plan_overlap = overlap_score(getattr(prediction, "implementation_plan", ""), getattr(example, "implementation_plan", ""))
            code_overlap = overlap_score(getattr(prediction, "code_changes", ""), getattr(example, "code_changes", ""))
            tests_overlap = overlap_score(getattr(prediction, "tests", ""), getattr(example, "tests", ""))
            commit_overlap = overlap_score(getattr(prediction, "commit_message", ""), getattr(example, "commit_message", ""))
            behavior = (0.25 * plan_overlap) + (0.30 * code_overlap) + (0.25 * tests_overlap) + (0.20 * commit_overlap)
        elif stage == "qa":
            verdict_match = 1.0 if normalize_verdict(getattr(prediction, "qa_verdict", "")) == normalize_verdict(getattr(example, "qa_verdict", "")) else 0.0
            merge_match = 1.0 if normalize_verdict(getattr(prediction, "merge_safe", "")) == normalize_verdict(getattr(example, "merge_safe", "")) else 0.0
            report_overlap = overlap_score(getattr(prediction, "verification_report", ""), getattr(example, "verification_report", ""))
            bugs_overlap = overlap_score(getattr(prediction, "bugs_found", ""), getattr(example, "bugs_found", ""))
            behavior = (0.35 * verdict_match) + (0.35 * merge_match) + (0.20 * report_overlap) + (0.10 * bugs_overlap)
        else:  # triage
            role_match = 1.0 if normalize_role(getattr(prediction, "engineer_role", "")) == normalize_role(getattr(example, "engineer_role", "")) else 0.0
            tests_overlap = overlap_score(getattr(prediction, "acceptance_tests", ""), getattr(example, "acceptance_tests", ""))
            dispatch_overlap = overlap_score(getattr(prediction, "dispatch_note", ""), getattr(example, "dispatch_note", ""))
            priority_overlap = overlap_score(getattr(prediction, "priority_assessment", ""), getattr(example, "priority_assessment", ""))
            behavior = (0.35 * role_match) + (0.25 * tests_overlap) + (0.25 * dispatch_overlap) + (0.15 * priority_overlap)

        return round((0.35 * base_quality) + (0.65 * behavior), 4)
    return metric


def compile_stage(stage: str, min_examples: int = 50):
    """Compile an optimized DSPy program for a pipeline stage."""
    config = STAGE_CONFIG[stage]
    jsonl_path = TRAINING_DIR / config["jsonl"]

    if not jsonl_path.exists():
        print(f"ERROR: {jsonl_path} not found. Run reconstruct-full.py first.")
        sys.exit(1)

    examples = load_examples(jsonl_path, config["min_score"], config["score_field"])
    print(f"Loaded {len(examples)} examples from {jsonl_path} (min_score={config['min_score']})")

    if len(examples) < min_examples:
        print(f"SKIP: Need {min_examples} examples, have {len(examples)}. Collect more data.")
        sys.exit(0)

    # Cap at 80 highest-scoring examples — BootstrapFewShot only needs enough
    # to find good demos (max_bootstrapped=4, max_labeled=8), not hundreds.
    examples.sort(key=lambda x: x.get(config["score_field"], 0), reverse=True)
    examples = examples[:80]
    print(f"Using top {len(examples)} examples for training (sorted by score)")

    # Convert raw dicts to dspy.Example objects
    # Only include fields that the signature knows about (input + output fields)
    sig = config["signature"]
    valid_fields = set(sig.input_fields.keys()) | set(sig.output_fields.keys())
    input_field_names = list(sig.input_fields.keys())

    train = []
    for ex in examples:
        filtered = {k: v for k, v in ex.items() if k in valid_fields}
        train.append(dspy.Example(**filtered).with_inputs(*input_field_names))

    # Create DSPy program
    program = dspy.Predict(config["signature"])

    # Compile with BootstrapFewShot
    metric = make_metric(stage, config["score_field"])
    optimizer = BootstrapFewShot(
        metric=metric,
        max_bootstrapped_demos=4,
        max_labeled_demos=8,
    )

    compiled = optimizer.compile(program, trainset=train)

    # Save compiled program
    PROGRAMS_DIR.mkdir(exist_ok=True)
    output_path = PROGRAMS_DIR / f"{stage}-optimized.json"
    compiled.save(str(output_path))
    print(f"Saved compiled program to {output_path}")

    return compiled


def main():
    parser = argparse.ArgumentParser(description="Compile DSPy programs from quality metrics")
    parser.add_argument("--stage", required=True, choices=STAGE_CONFIG.keys())
    parser.add_argument("--min-examples", type=int, default=50)
    parser.add_argument("--model", default="anthropic/claude-sonnet-4-6",
                        help="LLM to use for compilation")
    args = parser.parse_args()

    # Configure DSPy LM
    lm = dspy.LM(args.model)
    dspy.configure(lm=lm)

    compile_stage(args.stage, args.min_examples)


if __name__ == "__main__":
    main()
