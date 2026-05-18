# Board-Review Contract Tests

This directory contains the deterministic offline contract suite around board-review routing and state machinery.

## Required Gate

Run this command after any change to the board-review framework, precheck wake routing, product state contract, task queue intake, or run-lock handling:

```bash
bash framework/board-review/tests/run.sh
```

The expectation is 100% pass because the suite must avoid network calls, real GitHub state, live agents, and real OpenClaw sessions. Use mocked `gh` and `openclaw` commands plus temporary state files.

## Stable Invariants

- Live GitHub `status:*` labels are the only actionability source.
- No shared fleet-status Markdown file is read to decide whether a ticket is actionable.
- Product wake prompts include the correct product context block: product name, product state path, and task queue path.
- Precheck writes `PRECHECK_STATE.json` with `actionableIssues` and no stale `openIssues`.
- ChurnPilot and Framework task queues route independently to their own CTO sessions and queue files.
- A live run lock prevents duplicate wakes.
- A stale or dead run lock gets cleared.

Keep these tests implementation-tolerant. They should fail only when the external board-review contract changes or regresses, not because private helper names or internal implementation details move.
