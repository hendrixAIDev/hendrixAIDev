# Stateful CTO per Product — Design Note

**Status:** Draft for review  
**Date:** 2026-04-06  
**Author:** Hendrix  
**Location:** `framework/board-review/docs/CTO_STATEFUL_PRODUCT_ORCHESTRATION.md`

---

## Summary

The current Board Review system treats the CTO as a *stateless coordinator* operating a mostly fixed workflow:

```text
status:new -> engineer -> code review -> QA -> CTO review -> close
```

That has worked well for predictable implementation loops, but it mixes two different responsibilities:

1. **Coordination** — monitor ticket state, dispatch the next role, enforce gates, report status.
2. **Planning / strategic orchestration** — decide *which* workflow a ticket should follow, whether a stage is necessary, what kind of specialist should act next, and when durable project memory should be updated.

This note proposes a clearer split:

- **CTO becomes stateful at the product level** and acts as the strategic orchestrator for exactly one product.
- **Sub-agents remain stateless** and execute isolated, well-scoped work.
- The system shifts from a *fixed pipeline engine* to a *workflow/policy engine* where the CTO selects the appropriate path per ticket.

The key idea is *not* “persistent memory hidden inside a single long-lived session.” The key idea is *persistent, inspectable product state stored in artifacts* so any fresh CTO session can resume safely.

---

## Problem Statement

### What works today

The current Board Review design is good at:

- one-pass stateless operation
- clear label-driven automation
- isolated execution via sub-agents
- deterministic handoff gates
- avoiding token waste from long-lived waiting sessions

### What is limiting

The current design also hard-codes assumptions that are too rigid for product-level orchestration:

- it assumes the normal route is always `engineer -> reviewer -> QA -> CTO`
- it treats `status:new` as “dispatch engineer” rather than “CTO decides next best action”
- it assumes QA is always mandatory, even when the change may be low-risk or non-user-facing
- it has limited support for non-engineering workflows, such as:
  - product analysis
  - launch/readiness review
  - trust/risk review
  - content/positioning work
  - UX/design exploration
- it frames the CTO as a traffic cop for a fixed assembly line instead of the product owner/operator deciding how a ticket should move

### Resulting design smell

The current system uses the CTO as a *coordinator* while baking *planning* into the pipeline itself.

That means:

- strategic decisions are implicit instead of explicit
- workflow variation is awkward
- exceptions feel like violations instead of first-class behavior
- the system is harder to extend to multiple products with different operating styles

---

## Design Goals

### Primary goals

1. **Make the CTO the strategic orchestrator for one product**
2. **Keep sub-agents stateless and replaceable**
3. **Allow multiple valid workflows instead of a single forced sequence**
4. **Store product state in durable, inspectable artifacts**
5. **Preserve label-driven automation and precheck wakeups**

### Non-goals

This proposal does *not* aim to:

- make CTO sessions long-lived background daemons
- give sub-agents persistent product memory
- remove labels or GitHub as the operational control plane
- remove deterministic gates where they are still valuable
- immediately rewrite the entire framework in one step

---

## Proposed Model

## 1. CTO becomes stateful *per product*

Each product gets exactly one conceptual CTO role.

Examples:

- ChurnPilot CTO
- StatusPulse CTO
- Personal Brand CTO

A CTO session is still triggered by precheck and can still be short-lived, but it now operates against a *persistent product context*.

That CTO is responsible for:

- maintaining the product’s operating model
- choosing the right workflow template for each ticket
- deciding the next action for each ticket
- deciding when to escalate to JJ
- deciding when ticket-local notes are not enough and durable product docs need updating

### Important clarification

“Stateful CTO” does *not* mean:

- one immortal chat thread that must stay alive forever
- hidden reasoning only available inside one runtime session

It means:

- there is durable product state that survives sessions
- any fresh CTO run can reconstruct context from artifacts
- decisions are visible and auditable

---

## 2. Sub-agents remain stateless

Sub-agents should continue to be:

- isolated
n- disposable
- role-specific
- execution-oriented
- responsible only for their assigned task plus output handoff

A sub-agent should *not* own product strategy.

A sub-agent should *not* decide the global workflow.

A sub-agent should *not* maintain long-term memory beyond:

- its work product
- its ticket comment
- its status-label update
- any requested artifact updates

This keeps the system debuggable and prevents silent drift in product logic.

---

## 3. Replace the fixed pipeline with workflow templates

Instead of assuming every ticket follows one universal route, the CTO chooses from reusable workflow templates.

### Example workflow templates

#### A. Feature implementation workflow

Use when the ticket requires building or modifying product behavior.

Typical path:

```text
CTO triage
-> implementation agent
-> code review
-> QA or deploy verification (if needed)
-> CTO review / close
```

#### B. Bugfix workflow

Use when a concrete bug already has a likely implementation path.

Typical path:

```text
CTO triage
-> implementation agent
-> focused review
-> targeted verification
-> CTO review / close
```

#### C. Product analysis workflow

Use when the right move is not yet implementation.

Typical path:

```text
CTO triage
-> product analyst
-> CTO planning decision
-> create follow-up implementation/design tickets or close with recommendation
```

#### D. UX / design workflow

Use when user journey, layout, or interaction design must be clarified before implementation.

Typical path:

```text
CTO triage
-> UX / user-journey / design agent
-> CTO review
-> implementation ticket(s)
```

#### E. Trust / risk / policy workflow

Use when legal, trust, or risk concerns dominate.

Typical path:

```text
CTO triage
-> trust/risk auditor
-> CTO review
-> JJ escalation if business decision required
```

#### F. Content / launch workflow

Use when the output is messaging rather than code.

Typical path:

```text
CTO triage
-> content engineer / launch reviewer
-> editorial review
-> CTO review / close
```

### Why templates instead of a free-for-all

We do *not* want the system to become vague or improvised.

Templates give:

- standard routes
- explicit branching logic
- room for exceptions
- easier audits and docs

The CTO should choose among *known workflow families*, not invent a brand-new process every time.

---

## 4. CTO as policy engine, not just coordinator

Under the new model, the CTO’s job is:

1. inspect ticket state and product context
2. classify the ticket
3. select a workflow template
4. choose the next role
5. decide what validation is required
6. decide whether the result should become durable project memory

This is a different posture from:

> “Ticket is at label X, therefore always send role Y.”

Instead, the posture becomes:

> “Given this product, this ticket, this risk level, and this prior history, what is the next best action?”

---

## Proposed State Model

## Principle: state must be *recoverable and inspectable*

The dangerous version of “stateful CTO” is hidden state trapped inside a session.

The preferred version is explicit state stored in artifacts any future session can load.

### State should live in these places

#### 1. GitHub ticket state

GitHub remains the operational source of truth for ticket-level activity:

- labels
- comments
- dependencies
- acceptance tests
- completion / failure notes
- escalation history

#### 2. Product-level orchestration state file

Add a per-product orchestration memory file, for example:

```text
framework/board-review/state/churn_copilot.json
framework/board-review/state/statuspulse.json
```

This file can track:

- current operating mode for the product
- active workflow policies
- ticket routing notes that matter across sessions
- unresolved product-wide decisions
- last CTO plan checkpoints
- known recurring failure patterns

This should be compact and operational, not a dumping ground.

#### 3. Product-level planning docs

When insight is durable and useful beyond one ticket, promote it into product docs, for example:

```text
projects/[product]/plans/
projects/[product]/docs/
```

Examples:

- a signup flow redesign decision
- rollout policy for Stripe ON/OFF behavior
- a canonical workflow for launch readiness

#### 4. Board review status artifact

`BOARD_REVIEW_STATUS.md` remains useful as a cross-session snapshot, but it should become more summary-oriented and less overloaded as the only continuity mechanism.

---

## Ticket Routing Model

## New interpretation of `status:new`

Today, `status:new` mostly means:

> dispatch an engineer

Under the new model, `status:new` should mean:

> CTO must decide the next best action for this product and this ticket

Possible next actions:

- dispatch fullstack engineer
- dispatch backend engineer
- dispatch frontend engineer
- dispatch product analyst
- dispatch UX / user-journey agent
- dispatch trust/risk auditor
- dispatch content engineer
- block on dependency
- escalate to JJ
- split the ticket into follow-up tickets
- close as invalid / superseded / already solved
- write/update a durable planning doc before dispatching further work

That makes `status:new` a true planning entry point instead of a synonym for engineering.

---

## Validation Model

## QA becomes conditional, not automatic

One of the main reasons for this redesign is that the CTO should be allowed to choose validation depth.

### Proposed rule

Every ticket still requires *validation*, but not every ticket requires the *same validation role or sequence*.

Examples:

- user-facing UI change -> deploy verification / QA strongly recommended
- backend-only refactor with strong automated coverage -> reviewer + test evidence may be enough
- product analysis ticket -> no QA; CTO review is the real gate
- content deliverable -> editorial review, not product QA
- trust/risk assessment -> policy review, not browser QA

### Safer framing

We should avoid a blanket “skip QA” doctrine.

Instead:

- *all tickets require an explicit validation plan chosen by CTO*
- QA is one possible validation mode, not the only one

That keeps rigor while restoring flexibility.

---

## Label Model

We can preserve most current labels while changing how they are interpreted.

### Option A — Minimal label change

Keep existing labels:

- `status:new`
- `status:in-progress`
- `status:review`
- `status:verification`
- `status:cto-review`
- `status:blocked`
- `status:needs-jj`
- `status:done`

But reinterpret them more generically:

- `status:review` = some formal review is needed, not always code review
- `status:verification` = some formal validation is needed, not always QA

### Option B — Expand labels later if needed

If the system becomes too overloaded, add more explicit phase labels later, for example:

- `status:analysis`
- `status:design`
- `status:policy-review`
- `status:content-review`

### Recommendation

Start with *Option A*.

Keep the existing labels first and change CTO routing behavior before changing the public label vocabulary. That reduces migration risk.

---

## Responsibilities by Role

## CTO responsibilities

The product CTO should:

- own one product context
- choose workflow templates
- define ticket validation plans
- decide next actions on `status:new`
- decide whether a result needs durable documentation
- decide when a retry is justified versus when escalation is needed
- maintain product orchestration state
- close tickets when satisfied

The CTO should *not*:

- do the implementation work directly
- become a long-running waiter on sub-agent completion
- hide critical state inside private session context only

## Sub-agent responsibilities

Sub-agents should:

- execute a narrow role task
- produce artifacts/comments
- update labels as instructed
- stop when done

Sub-agents should *not*:

- choose the global workflow
- redefine product priorities
- maintain persistent product strategy

---

## Suggested Artifact Layout

```text
framework/board-review/
├── BOARD_REVIEW.md
├── TICKET_SYSTEM.md
├── BOARD_REVIEW_STATUS.md
├── docs/
│   └── CTO_STATEFUL_PRODUCT_ORCHESTRATION.md
├── state/
│   ├── churn_copilot.json
│   └── statuspulse.json
└── workflows/
    ├── feature-implementation.md
    ├── bugfix.md
    ├── product-analysis.md
    ├── ux-design.md
    ├── trust-risk.md
    └── content-launch.md
```

### Purpose of each new area

- `docs/` — design notes and reviewed architecture docs
- `state/` — compact recoverable per-product operational state
- `workflows/` — reusable workflow templates the CTO can select from

---

## Example Operating Loop

A future CTO pass for ChurnPilot might work like this:

1. precheck wakes the ChurnPilot CTO
2. CTO loads:
   - current ticket board state
   - `framework/board-review/state/churn_copilot.json`
   - relevant project docs/plans
3. CTO sees Ticket A is `status:new`
4. CTO classifies it as *product analysis*, not implementation
5. CTO dispatches Product Analyst, not Engineer
6. analyst returns recommendation and updates label
7. next CTO run reviews recommendation
8. CTO either:
   - creates follow-up implementation tickets, or
   - dispatches a UX agent, or
   - escalates to JJ, or
   - closes the analysis ticket

Another ticket for the same product may still follow classic implementation -> review -> verification -> CTO close.

That is the point: *same product CTO, different ticket workflows, one consistent orchestration layer*.

---

## Migration Strategy

This should be done incrementally.

### Phase 1 — Add design/docs only

- add this design note
- review and refine terminology
- identify which current assumptions in `BOARD_REVIEW.md` are too rigid

### Phase 2 — Introduce workflow templates

- define 4-6 canonical workflow documents
- keep existing labels
- update CTO docs so triage selects a workflow template instead of auto-defaulting to engineer

### Phase 3 — Add per-product state files

- create `framework/board-review/state/[product].json`
- keep them minimal
- define exactly what is allowed there

### Phase 4 — Update dispatch logic

- route based on workflow template + ticket type
- make validation mode explicit per ticket
- stop assuming QA is mandatory in all cases

### Phase 5 — Revisit labels

- only after workflow routing works well
- decide whether broader labels are sufficient or whether more explicit labels are warranted

---

## What should change in current docs

### `BOARD_REVIEW.md`

Should change from:

- a universal fixed 6-phase pipeline

Toward:

- CTO operating model
- workflow selection rules
- product-state loading rules
- validation selection rules
- dispatch policy by workflow type

### `TICKET_SYSTEM.md`

Should change from:

- one linear success path

Toward:

- generic status semantics
- role-specific handoff rules by workflow
- clear definition of who may set which labels in which contexts

### `BOARD_REVIEW_STATUS.md`

Should remain:

- a useful summary artifact

But should not be the only place where product continuity lives.

---

## Risks and Mitigations

### Risk 1: Too much flexibility creates chaos

**Mitigation:** use explicit workflow templates, not ad-hoc improvisation.

### Risk 2: “Stateful CTO” becomes hidden session memory

**Mitigation:** require durable state in files/docs/comments, not only in runtime context.

### Risk 3: Label semantics become ambiguous

**Mitigation:** keep labels stable at first, and document their broader meaning clearly.

### Risk 4: CTO becomes a bottleneck

**Mitigation:** keep sub-agents stateless and parallelizable; only centralize routing and strategic decisions.

### Risk 5: Validation quality drops when QA is optional

**Mitigation:** require an explicit validation plan per ticket, chosen by CTO and visible in the dispatch note.

---

## Recommendation

I recommend adopting this direction.

Specifically:

1. treat the CTO as the *stateful strategic orchestrator for one product*
2. keep sub-agents *stateless and isolated*
3. redefine `status:new` as *CTO planning required*, not *engineer dispatch required*
4. introduce *workflow templates* as the main abstraction
5. make *validation explicit and context-dependent* instead of assuming QA is always mandatory
6. store state in *recoverable artifacts*, not hidden session memory

That gives us a system that is:

- more flexible
- more product-aware
- easier to extend
- still auditable
- still automation-friendly

---

## Open Questions for Review

1. Should each product have its own CTO prompt/doc, or one shared CTO doc with product-specific state files?
2. Should `status:review` and `status:verification` remain generic, or do we want richer labels later?
3. What is the minimum safe schema for `framework/board-review/state/[product].json`?
4. Which workflow templates are required on day one versus later?
5. Should product analysis be allowed to create new tickets directly, or only recommend them for CTO review?
6. How much of the current retry-limit logic should remain global versus workflow-specific?

---

## Proposed Next Step

If this direction looks right, the next concrete implementation step should be:

1. define the workflow template documents
2. define the per-product state-file schema
3. rewrite `BOARD_REVIEW.md` triage so `status:new` means *classify + choose workflow + choose next role*

That would change the system at the right abstraction layer without forcing a risky full rewrite first.
