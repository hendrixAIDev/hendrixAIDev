# Board Review

Entry point for the board review system.

## Core Docs

- `BOARD_REVIEW.md` — CTO operating guide
- `TICKET_SYSTEM.md` — sub-agent ticket and status rules
- `BOARD_REVIEW_STATUS.md` — cross-run status snapshot
- `REPOS.conf` — monitored repos
- `state/README.md` — product state artifact contract
- `docs/CTO_STATEFUL_PRODUCT_ORCHESTRATION.md` — architecture and migration plan
- `workflows/` — workflow examples / references for CTO

## Current Strategy

Board review is moving to a CTO-led product orchestration model.

Key points:
- one persistent named CTO session per product
- precheck wakes the correct product CTO session
- CTO owns strategy, planning, and next-step decisions
- workflows are references, not a rigid router
- sub-agents work under `status:in-progress`, then normally return tickets to `status:new`
- CTO re-triages after each completed work pass
- validation is required before closure
- per-product state lives under `state/<product>.*`
- we define the shared state contract now, while each product CTO defines its own actual contents later

## Migration Direction

Done so far:
- product CTO session mapping defined in `BOARD_REVIEW.md`
- precheck routes wakes by product CTO session
- `BOARD_REVIEW.md` and `TICKET_SYSTEM.md` aligned around CTO-led re-triage
- shared state artifact contract defined
- workflow references added

Next:
- create starter per-product state files
- teach live CTO runs to read/write those state files consistently
