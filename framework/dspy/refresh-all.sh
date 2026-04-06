#!/usr/bin/env bash
# refresh-all.sh — one-command DSPy refresh/status workflow
#
# Rebuilds stage corpora from metrics, optionally expands with full GitHub history,
# merges training sets conservatively, recompiles all DSPy programs, backfills
# shadow labels, prints shadow stats, and reports ticket coverage across the 4
# primary GitHub repos.
#
# Usage examples:
#   framework/dspy/refresh-all.sh --yes
#   framework/dspy/refresh-all.sh --full-history --yes
#   framework/dspy/refresh-all.sh --full-history --shadow-repo hendrixAIDev/churn_copilot_hendrix --shadow-tickets 181,180,177 --yes
#   framework/dspy/refresh-all.sh --status-only

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$SCRIPT_DIR/.venv/bin/python"
DEFAULT_MODEL="openai/gpt-4.1-mini"
MIN_EXAMPLES=50
FULL_HISTORY=false
DO_COMPILE=true
STATUS_ONLY=false
AUTO_YES=false
SHADOW_REPO=""
SHADOW_TICKETS=""

usage() {
  cat <<'EOF'
Usage: refresh-all.sh [options]

Options:
  --full-history              Expand corpora using full GitHub closed-ticket history
  --no-compile                Rebuild/merge only; skip compile stage
  --status-only               Only backfill labels, analyze shadow log, and print coverage
  --shadow-repo OWNER/REPO    Repo for post-compile shadow sample
  --shadow-tickets A,B,C      Comma-separated ticket numbers for fresh shadow sample
  --yes                       Skip confirmation prompt
  -h, --help                  Show this help
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --full-history) FULL_HISTORY=true ;;
    --no-compile) DO_COMPILE=false ;;
    --status-only) STATUS_ONLY=true; DO_COMPILE=false ;;
    --shadow-repo) SHADOW_REPO="${2:-}"; shift ;;
    --shadow-tickets) SHADOW_TICKETS="${2:-}"; shift ;;
    --yes) AUTO_YES=true ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
  esac
  shift
done

if [[ ! -x "$VENV_PY" ]]; then
  echo "ERROR: Missing DSPy venv python at $VENV_PY" >&2
  exit 1
fi

if [[ -z "${OPENAI_API_KEY:-}" && "$STATUS_ONLY" != true ]]; then
  if command -v security >/dev/null 2>&1; then
    export OPENAI_API_KEY="$(security find-generic-password -a "hendrix.ai.dev@gmail.com" -s "openai.com" -w 2>/dev/null || true)"
  fi
fi

if [[ "$STATUS_ONLY" != true && -z "${OPENAI_API_KEY:-}" ]]; then
  echo "ERROR: OPENAI_API_KEY not set and could not be loaded from Keychain." >&2
  exit 1
fi

if [[ "$AUTO_YES" != true ]]; then
  echo "DSPy refresh plan:"
  echo "  status-only : $STATUS_ONLY"
  echo "  full-history: $FULL_HISTORY"
  echo "  compile     : $DO_COMPILE"
  echo "  shadow repo : ${SHADOW_REPO:-<none>}"
  echo "  shadow ticks: ${SHADOW_TICKETS:-<none>}"
  printf "Continue? [y/N] "
  read -r ans
  [[ "$ans" =~ ^[Yy]$ ]] || exit 0
fi

run_merge() {
  "$VENV_PY" - <<'PY'
import json
from pathlib import Path
base=Path('/Users/hendrix/.openclaw/workspace/framework/dspy/training-data')

def score(ex):
    return float(ex.get('_score',0) or 0)

def key(ex, stage):
    if stage=='code-review':
        return (ex.get('_repo'), ex.get('_ticket'), ex.get('verdict'), (ex.get('review_comment') or '')[:180])
    if stage=='qa':
        return (ex.get('_repo'), ex.get('_ticket'), ex.get('qa_verdict'), (ex.get('verification_report') or '')[:180])
    if stage=='engineer':
        return (ex.get('_repo'), ex.get('_ticket'), (ex.get('implementation_plan') or '')[:180])
    return (ex.get('_repo'), ex.get('_ticket'), ex.get('engineer_role'), (ex.get('dispatch_note') or '')[:180])

for stage in ['code-review','engineer','qa','triage']:
    primary=base/f'{stage}-training.jsonl'
    full=base/f'{stage}-training-full.jsonl'
    merged=[]
    seen=set()
    for source in [primary, full]:
        if not source.exists():
            continue
        for line in source.open():
            if not line.strip():
                continue
            ex=json.loads(line)
            ex['_merged_source']=source.name
            k=key(ex, stage)
            if k in seen:
                continue
            if source==full and score(ex) < 0.6:
                continue
            seen.add(k)
            merged.append(ex)
    out=base/f'{stage}-training.jsonl'
    with out.open('w') as f:
        for ex in merged:
            f.write(json.dumps(ex)+'\n')
    print(f'{stage}: merged -> {len(merged)} examples')
PY
}

print_coverage() {
  "$VENV_PY" - <<'PY'
import json, subprocess
from pathlib import Path
repos=['hendrixAIDev/churn_copilot_hendrix','hendrixAIDev/character-life-sim','hendrixAIDev/hendrixAIDev','zrjaa1/openclaw-assistant']
all_tickets=set()
for repo in repos:
    out=subprocess.check_output(['gh','issue','list','--repo',repo,'--state','closed','--limit','500','--json','number,body'], text=True)
    for issue in json.loads(out):
        if len((issue.get('body') or '').strip()) >= 20:
            all_tickets.add((repo, str(issue['number'])))
base=Path('/Users/hendrix/.openclaw/workspace/framework/dspy/training-data')
for stage in ['code-review','engineer','qa','triage']:
    p=base/f'{stage}-training.jsonl'
    have={(obj.get('_repo'), str(obj.get('_ticket'))) for line in p.open() if line.strip() for obj in [json.loads(line)] if obj.get('_repo') in repos}
    missing=sorted(all_tickets-have)
    print(f'coverage:{stage}: {len(have)}/{len(all_tickets)} tickets across 4 repos')
    if missing:
        print('  missing:', ', '.join(f'{r}#{t}' for r,t in missing[:12]))
PY
}

if [[ "$STATUS_ONLY" != true ]]; then
  echo "==> Rebuilding metric-derived corpora"
  "$VENV_PY" "$SCRIPT_DIR/reconstruct.py" --stage all

  if [[ "$FULL_HISTORY" == true ]]; then
    echo "==> Expanding from full GitHub history"
    "$VENV_PY" "$SCRIPT_DIR/reconstruct-full.py" --stage all
    echo "==> Merging metric + full-history corpora"
    run_merge
  fi

  if [[ "$DO_COMPILE" == true ]]; then
    echo "==> Compiling all stages with $DEFAULT_MODEL"
    for stage in code-review engineer qa triage; do
      "$VENV_PY" "$SCRIPT_DIR/compile.py" --stage "$stage" --min-examples "$MIN_EXAMPLES" --model "$DEFAULT_MODEL"
    done
  fi

  if [[ -n "$SHADOW_REPO" && -n "$SHADOW_TICKETS" ]]; then
    echo "==> Running fresh shadow sample"
    IFS=',' read -r -a tickets <<< "$SHADOW_TICKETS"
    for ticket in "${tickets[@]}"; do
      "$SCRIPT_DIR/shadow-run.sh" --stage all --repo "$SHADOW_REPO" --ticket "$ticket"
    done
  fi
fi

echo "==> Backfilling labels"
"$SCRIPT_DIR/shadow-run.sh" --backfill-labels

echo "==> Shadow analysis"
"$SCRIPT_DIR/shadow-run.sh" --analyze

echo "==> Training-data coverage across 4 repos"
print_coverage

echo "==> DSPy refresh complete"
