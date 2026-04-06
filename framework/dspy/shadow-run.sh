#!/bin/bash
# Shadow evaluation runner — called by CTO Board Review during Phase 4 (ticket closure)
#
# Usage: ./shadow-run.sh --stage code-review --repo owner/repo --ticket 123
#        ./shadow-run.sh --backfill-labels
#
# Runs both baseline and optimized DSPy prompts on the ticket, logs comparison
# to shadow-log.jsonl. Returns quickly (~10-20s). Does NOT affect the pipeline
# decision — purely observational.
#
# Prerequisites:
#   - OPENAI_API_KEY in environment (or macOS keychain)
#   - DSPy venv at framework/dspy/.venv

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Get OpenAI key from keychain if not in env
if [ -z "${OPENAI_API_KEY:-}" ]; then
    OPENAI_API_KEY=$(security find-generic-password -a "hendrix.ai.dev@gmail.com" -s "openai.com" -w 2>/dev/null || true)
    export OPENAI_API_KEY
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "ERROR: No OPENAI_API_KEY available"
    exit 1
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Run shadow evaluation (shadow-run.py defaults to openai/gpt-4.1-mini)
cd "$SCRIPT_DIR"
PYTHONUNBUFFERED=1 python -u shadow-run.py "$@"
