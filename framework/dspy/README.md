# DSPy Shadow Mode Pipeline

**Purpose:** Optimize board review prompts using labeled quality data from `framework/metrics/`.
**Status:** ✅ All 4 stages compiled. Shadow mode ACTIVE — runs on every ticket closure in Phase 4.

## Architecture

```
Metrics (JSONL)          DSPy Compilation         Shadow Evaluation
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ review-quality   │────▶│ compile.py       │────▶│ shadow-eval.py   │
│ engineer-quality │     │ - Load examples  │     │ - Run both       │
│ qa-quality       │     │ - Define sigs    │     │   prompts        │
│ triage-quality   │     │ - Optimize       │     │ - Compare scores │
└─────────────────┘     │ - Save program   │     │ - Log results    │
                        └──────────────────┘     └──────────────────┘
                                │                         │
                        ┌───────▼───────┐         ┌───────▼───────┐
                        │ programs/     │         │ shadow-log.jsonl│
                        │ *.json        │         │ (A/B results)  │
                        └───────────────┘         └───────────────┘
```

## Stages

| Stage | Training Examples | Compiled Program | Demos | Status |
|-------|------------------|-----------------|-------|--------|
| Code Review | 244 (from 4 repos) | `code-review-optimized.json` (45K) | 8 | ✅ Compiled + Shadow active |
| Engineering | 244 | `engineer-optimized.json` (49K) | 8 | ✅ Compiled + Shadow active |
| QA | 244 | `qa-optimized.json` (59K) | 8 | ✅ Compiled + Shadow active |
| Triage | 244 | `triage-optimized.json` (21K) | 8 | ✅ Compiled + Shadow active |

**Data source:** All 244 closed tickets across 4 repos (ChurnPilot: 155, Character Life Sim: 62, hendrixAIDev: 23, openclaw-assistant: 4).
**Compiled on:** 2026-03-14 using `openai/gpt-4.1-mini` via BootstrapFewShot.

## DSPy Signatures

### CodeReviewSignature (first target)
```python
class CodeReviewSignature(dspy.Signature):
    """Review code changes for a ticket and produce a verdict."""
    
    ticket_body: str = dspy.InputField(desc="GitHub issue body with requirements and acceptance tests")
    diff: str = dspy.InputField(desc="git diff of changes (experiment..branch)")
    conventions: str = dspy.InputField(desc="CONVENTIONS.md content")
    lint_output: str = dspy.InputField(desc="ruff check output on changed files")
    streamlit_gotchas: str = dspy.InputField(desc="Known Streamlit pitfalls from knowledge/streamlit-gotchas.md")
    
    verdict: str = dspy.OutputField(desc="APPROVE or REJECT")
    findings: str = dspy.OutputField(desc="List of findings with severity P1-P3")
    scope_check: str = dspy.OutputField(desc="Whether changes stay within ticket scope")
    review_comment: str = dspy.OutputField(desc="GitHub comment for the ticket")
```

### EngineerSignature
```python
class EngineerSignature(dspy.Signature):
    """Implement a fix or feature for a ticket."""
    
    ticket_body: str = dspy.InputField(desc="GitHub issue body with requirements and acceptance tests")
    codebase_context: str = dspy.InputField(desc="Relevant source files and structure")
    conventions: str = dspy.InputField(desc="CONVENTIONS.md content")
    streamlit_gotchas: str = dspy.InputField(desc="Known Streamlit pitfalls (if applicable)")
    engineer_role: str = dspy.InputField(desc="fullstack, backend, or frontend")
    
    implementation_plan: str = dspy.OutputField(desc="Brief plan before coding")
    code_changes: str = dspy.OutputField(desc="Files modified/created with changes")
    tests: str = dspy.OutputField(desc="Test files matching acceptance criteria")
    commit_message: str = dspy.OutputField(desc="Conventional commit message")
```

## Files

| File | Purpose |
|------|---------|
| `README.md` | This file — architecture and status |
| `signatures.py` | DSPy signature definitions (4 signatures) |
| `compile.py` | Load training data, compile optimized programs |
| `reconstruct-full.py` | Pull all closed tickets from GitHub, build training JSONL |
| `refresh-all.sh` | One-command DSPy refresh: rebuild, optionally expand, compile, sample, backfill, analyze, and print coverage |
| `shadow-run.sh` | Shell wrapper — called by Board Review Phase 4 |
| `shadow-run.py` | Shadow comparison engine (baseline vs optimized) |
| `shadow-eval.py` | Original shadow evaluator (superseded by shadow-run.py) |
| `training-data/` | Enriched JSONL files from GitHub reconstruction |
| `programs/` | Saved compiled DSPy programs (4 JSON files) |
| `shadow-log.jsonl` | A/B comparison results (growing with each ticket closure) |
| `.venv/` | Python venv with dspy-ai installed |

## Shadow Mode Protocol (ACTIVE)

1. ✅ **Compile:** All 4 stages compiled (ongoing, not one-time)
2. ✅ **Shadow:** Board Review Phase 4 runs `shadow-run.sh` on every ticket closure
3. 🔄 **Compare:** Both outputs logged to `shadow-log.jsonl` with latency
4. 🔄 **Backfill labels:** Run `framework/dspy/shadow-run.sh --backfill-labels` to pull human scores/labels from `framework/metrics/*.jsonl`
5. ⏳ **Promote:** Only promote when optimized shows a meaningful repeatable win, not a tiny edge on mostly ties

## Steady-State Workflow (Recommended)

Treat DSPy as a continuous improvement loop, not a one-off migration.

### 1) Every ticket closure
- Board Review Phase 4 runs shadow evaluation for all stages on the closed ticket.
- Human/automation metrics continue landing in `framework/metrics/*.jsonl`.
- Shadow outputs append to `framework/dspy/shadow-log.jsonl`.

### 2) Daily or after a focused work block
- Run:
```bash
framework/dspy/shadow-run.sh --backfill-labels
framework/dspy/shadow-run.sh --analyze
```
- Goal: keep the shadow log labeled and detect drift early (model/auth failures, stage regressions, empty labels, etc.).

### 3) Weekly corpus maintenance
- Rebuild stage corpora from the higher-confidence metric path:
```bash
cd framework/dspy
.venv/bin/python reconstruct.py --stage all
```
- If a stage is still under target example count or lacks class balance, expand with bulk history mining:
```bash
.venv/bin/python reconstruct-full.py --stage all
```
- Merge bulk history examples conservatively. Prefer cleaner metric-derived examples when both exist.

### 4) When to recompile
Recompile when one or more of these are true:
- 25-50+ new labeled tickets have accumulated for a stage
- class balance improved materially (for example, code-review gained more REJECT examples, QA gained more FAIL examples)
- stage logic changed (new signatures, better reconstruction, better metric functions)
- shadow analysis shows the current optimized program is stale or underperforming

### 5) After every recompile
- Run a fresh shadow batch on several recently labeled tickets from different outcomes.
- Backfill labels again.
- Compare fresh post-compile shadow behavior, not just old pre-compile entries.

### 6) Promotion guardrail
Do **not** replace live role overlays just because optimized edges baseline by 1 win.
Promote only when:
- there are 20+ comparable labeled entries for that stage,
- optimized beats baseline by a meaningful margin,
- the gain survives a fresh post-compile shadow batch,
- and the outputs are qualitatively better, not just score-matched.

## Operating Principle

There are three kinds of DSPy work:
- **Plumbing repair** — fix broken model/auth/config/analysis logic
- **Data quality work** — improve reconstruction, labels, class balance, and target fidelity
- **Program refresh** — recompile after the first two improve

Only the first category is mostly one-time. The second and third are ongoing maintenance loops.

## Quick Commands

```bash
# Run shadow evaluation on a ticket
framework/dspy/shadow-run.sh --stage all --repo owner/repo --ticket 123

# Check shadow stats
framework/dspy/shadow-run.sh --analyze

# Backfill shadow labels from the existing metrics corpus
framework/dspy/shadow-run.sh --backfill-labels

# Recompile after collecting more data
cd framework/dspy && source .venv/bin/activate
OPENAI_API_KEY=... python compile.py --stage code-review --model openai/gpt-4.1-mini

# Rebuild training data from GitHub
python reconstruct-full.py --stage all

# One-command refresh + status summary
framework/dspy/refresh-all.sh --status-only
framework/dspy/refresh-all.sh --full-history --yes
```

## When to Recompile

- When 50+ new tickets have closed since last compilation (currently compiled with 244)
- When shadow analysis shows optimized is NOT winning (try MIPROv2 optimizer)
- After significant pipeline changes (new conventions, new gotchas)
