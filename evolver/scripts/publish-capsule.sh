#!/usr/bin/env bash
# publish-capsule.sh — Build and publish a Gene+Capsule+EvolutionEvent bundle to EvoMap hub
# Usage: publish-capsule.sh <capsule-json-file>
# Reads local capsule JSON → formats as GEP-A2A bundle → publishes to hub
set -euo pipefail

CAPSULE_FILE="${1:?Usage: publish-capsule.sh <capsule-json-file>}"
NODE_ID_FILE="${NODE_ID_FILE:-$HOME/.openclaw/workspace/framework/evolver/node_id.txt}"
HUB_URL="${A2A_HUB_URL:-https://evomap.ai}"

if [[ ! -f "$NODE_ID_FILE" ]]; then
  echo "ERROR: No node_id.txt found. Register first with POST /a2a/hello" >&2
  exit 1
fi

NODE_ID=$(cat "$NODE_ID_FILE")
MSG_ID="msg_$(date +%s)_$(openssl rand -hex 4)"
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Read capsule data
SIGNALS=$(jq -c '.signals // .trigger // []' "$CAPSULE_FILE")
SOLUTION=$(jq -r '.solution' "$CAPSULE_FILE")
SUMMARY=$(jq -r '.summary' "$CAPSULE_FILE")
CONFIDENCE=$(jq -r '.confidence // 0.8' "$CAPSULE_FILE")
STREAK=$(jq -r '.success_streak // 1' "$CAPSULE_FILE")
BLAST_FILES=$(jq -r '.blast_radius.files // 1' "$CAPSULE_FILE")
BLAST_LINES=$(jq -r '.blast_radius.lines // 10' "$CAPSULE_FILE")

GENE_SUMMARY="Strategy: ${SUMMARY#Fix for: }"

# Build Gene — use jq -cS for canonical sorted JSON (critical for hash)
GENE_NO_ID=$(jq -cS -n \
  --argjson signals "$SIGNALS" \
  --arg summary "$GENE_SUMMARY" \
  '{
    category: "repair",
    schema_version: "1.5.0",
    signals_match: $signals,
    summary: $summary,
    type: "Gene"
  }')
GENE_HASH=$(printf '%s' "$GENE_NO_ID" | shasum -a 256 | cut -d' ' -f1)
GENE=$(echo "$GENE_NO_ID" | jq --arg id "sha256:$GENE_HASH" '. + {asset_id: $id}')

# Build Capsule
CAPSULE_NO_ID=$(jq -cS -n \
  --argjson triggers "$SIGNALS" \
  --arg gene "sha256:$GENE_HASH" \
  --arg summary "$SOLUTION" \
  --argjson confidence "$CONFIDENCE" \
  --argjson blast_files "$BLAST_FILES" \
  --argjson blast_lines "$BLAST_LINES" \
  --argjson streak "$STREAK" \
  '{
    blast_radius: {files: $blast_files, lines: $blast_lines},
    confidence: $confidence,
    env_fingerprint: {arch: "arm64", platform: "darwin"},
    gene: $gene,
    outcome: {score: $confidence, status: "success"},
    schema_version: "1.5.0",
    success_streak: $streak,
    summary: $summary,
    trigger: $triggers,
    type: "Capsule"
  }')
CAPSULE_HASH=$(printf '%s' "$CAPSULE_NO_ID" | shasum -a 256 | cut -d' ' -f1)
CAPSULE=$(echo "$CAPSULE_NO_ID" | jq --arg id "sha256:$CAPSULE_HASH" '. + {asset_id: $id}')

# Build EvolutionEvent
EVENT_NO_ID=$(jq -cS -n \
  --arg cap "sha256:$CAPSULE_HASH" \
  --arg gene "sha256:$GENE_HASH" \
  --argjson confidence "$CONFIDENCE" \
  '{
    capsule_id: $cap,
    genes_used: [$gene],
    intent: "repair",
    mutations_tried: 1,
    outcome: {score: $confidence, status: "success"},
    total_cycles: 1,
    type: "EvolutionEvent"
  }')
EVENT_HASH=$(printf '%s' "$EVENT_NO_ID" | shasum -a 256 | cut -d' ' -f1)
EVENT=$(echo "$EVENT_NO_ID" | jq --arg id "sha256:$EVENT_HASH" '. + {asset_id: $id}')

echo "=== Publishing bundle ===" >&2
echo "Gene:    sha256:$GENE_HASH" >&2
echo "Capsule: sha256:$CAPSULE_HASH" >&2
echo "Event:   sha256:$EVENT_HASH" >&2
echo "Node:    $NODE_ID" >&2
echo "Hub:     $HUB_URL" >&2
echo "" >&2

# Publish
ENVELOPE=$(jq -n \
  --arg msg_id "$MSG_ID" \
  --arg sender "$NODE_ID" \
  --arg ts "$TIMESTAMP" \
  --argjson gene "$GENE" \
  --argjson capsule "$CAPSULE" \
  --argjson event "$EVENT" \
  '{
    protocol: "gep-a2a",
    protocol_version: "1.0.0",
    message_type: "publish",
    message_id: $msg_id,
    sender_id: $sender,
    timestamp: $ts,
    payload: { assets: [$gene, $capsule, $event] }
  }')

curl -s -X POST "${HUB_URL}/a2a/publish" \
  -H "Content-Type: application/json" \
  -d "$ENVELOPE" | jq .
