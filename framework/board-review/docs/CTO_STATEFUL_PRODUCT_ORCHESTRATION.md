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

In OpenClaw terms, each product CTO should exist as a **dedicated persistent named automation session**, not the main session and not an isolated one-shot session.

Examples:

- `session:cto-churnpilot`
- `session:cto-statuspulse`
- `session:cto-personal-brand`

The role definition stays shared and cached, while product-specific state is loaded from durable artifacts.

Each wake still behaves like a short pass: load state, act, delegate, exit. But the session identity remains stable per product, which gives the system a clean operational thread without mixing CTO automation into the main human-facing session.

That CTO is responsible for:

- maintaining the product’s operating model
- choosing the right workflow template for each ticket
- deciding the next action for each ticket
- deciding when to escalate to JJ
- deciding when ticket-local notes are not enough and durable product docs need updating

### Important clarification

“Stateful CTO” does *not* mean:

- the main session becomes the CTO control loop
- one immortal process sits around waiting for sub-agents
- hidden reasoning only available inside one runtime session

It means:

- each product has a stable CTO session identity in OpenClaw
- durable product state survives independently of chat context
- after compaction or wakeup, the CTO rehydrates from artifacts
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

The exact format does **not** have to be JSON. JSON is a reasonable default, but the CTO should be allowed to choose the artifact format that best preserves compact, recoverable operational state for that product.

The requirement is not “must be JSON.” The requirement is:

- durable
- inspectable
- easy to reload after context compaction
- easy for future CTO runs to update safely

This artifact can track:

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

Review decision: `status:review` and `status:verification` remain generic for now.

---

## Responsibilities by Role

## CTO responsibilities

The product CTO should:

- own one product context
- make strategic product decisions within CTO authority
- do planning and orchestration, not hands-on implementation
- choose workflow templates
- decide what kind of work is actually needed before dispatching anyone
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

The important constraint is: we are changing both the **operating model** and the **session model**. We should not rewrite everything at once.

The safest order is:

1. define the target architecture clearly
2. define stable per-product session identities
3. define the state artifacts those sessions reload
4. update the CTO operating docs
5. change precheck wake behavior
6. then evolve workflow routing and label semantics

### Phase 1 — Define product-to-session mapping

Goal: decide exactly how CTO exists in OpenClaw before changing runtime behavior.

Deliverables:

- define one persistent named CTO session per product
- define the canonical session keys, for example:
  - `session:cto-churnpilot`
  - `session:cto-statuspulse`
  - `session:cto-personal-brand`
- define which repo(s) and project path map to each CTO session
- define where product state for each session lives
- document this mapping in `framework/board-review/BOARD_REVIEW.md`

Rules:

- CTO does not run in the main session
- CTO is not a separate persona like Hendrix/Clawra by default
- CTO is a dedicated automation session construct
- one product, one CTO session identity

Why first:

Without this mapping, we cannot correctly redesign precheck or write reliable state-loading rules.

### Phase 2 — Define per-product state artifacts

Goal: make product continuity explicit and reloadable.

Deliverables:

- define the state artifact location per product
- define the minimum safe contents
- define update rules for the CTO
- define compaction recovery rules

Phase 2 decisions:

- canonical namespace: `framework/board-review/state/<product>.*`
- each product CTO reloads its state on every wake
- after context compaction, CTO re-reads state before acting
- state is for compact cross-run operational context only
- state must not duplicate GitHub ticket history or become a long-form journal
- durable product knowledge should be promoted into project docs/plans instead of staying in state
- we define the minimum shared contract now
- each product CTO defines the actual per-product contents later

Requirements:

- durable
- inspectable
- compact
- safe to reload every wake
- format-flexible, not hardcoded to JSON unless that proves best

Open question to resolve later if needed:

- whether all products should use the same artifact format for consistency, even though the architecture does not require JSON specifically

### Phase 3 — Update CTO operating docs

Goal: make the written operating model match the new architecture before changing automation.

Deliverables:

- update `BOARD_REVIEW.md`
- update `CTO_PROMPT.md`
- update any related dispatch guidance

Required changes:

- CTO is explicitly responsible for strategy, planning, and orchestration
- CTO delegates, does not implement
- CTO does not wait for sub-agents
- CTO must reload product state + project `README.md` after compaction and on each wake
- `status:new` becomes a planning entry point, not an automatic engineer-dispatch synonym
- validation is chosen explicitly by workflow, not assumed to always be QA

Why before automation:

The docs should define the contract before precheck and runtime behavior are changed.

### Phase 4 — Change wake model from isolated jobs to named product CTO sessions

Goal: move from today's isolated one-shot cron-created CTO runs to persistent per-product CTO session targets.

Current behavior:

- precheck creates an isolated one-shot CTO cron job
- the job runs once and disappears

Target behavior:

- precheck identifies which product has work
- precheck wakes the matching named CTO session for that product
- that session processes one pass and exits
- later work wakes the same product CTO session again

Deliverables:

- update precheck trigger logic
- update any job/session routing assumptions
- preserve watchdog behavior for stale WIP resets
- preserve cooldown / anti-spam protections

Success criteria:

- no work is routed to the main session
- no product wakes the wrong CTO session
- the same product always resumes in the same named CTO session

### Phase 5 — Introduce workflow templates into live routing

Goal: replace the fixed engineer-first assumption with controlled workflow selection.

Deliverables:

- define all workflow templates from day 1:
  - feature implementation
  - bugfix
  - product analysis
  - UX / design
  - trust / risk / policy
  - content / launch
- teach CTO triage to select a workflow template
- make dispatch routing depend on ticket type and workflow, not only current label

Constraints:

- keep existing generic labels for now
- avoid ad-hoc routing chaos by restricting triage to known workflow families

### Phase 6 — Revisit labels and validation semantics

Goal: decide whether the generic labels remain sufficient once workflow routing is real.

Review questions:

- are `status:review` and `status:verification` still clear enough?
- do we need explicit analysis/design/policy labels later?
- are validation expectations clear across non-engineering workflows?

Default decision for now:

- keep generic labels unless real usage proves they are too overloaded

### Phase 7 — Harden and simplify

Goal: clean up transitional logic after the new model is working.

Potential cleanup items:

- remove assumptions in old docs that still describe the fixed pipeline as universal
- simplify precheck once product-session routing is stable
- standardize state artifact format if useful
- add reporting/views that summarize product CTO state cleanly across sessions

## Recommended immediate next step

Start with **Phase 1: define product-to-session mapping**.

That is the smallest meaningful implementation step and it unlocks everything else cleanly.
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
- explicit session lifecycle rules (delegate, exit, let precheck wake the next pass)
- rules for operating inside persistent named per-product CTO sessions

This should become the primary operational guide once the stateful product orchestration model is adopted, while this document remains the architecture/design note.

### `TICKET_SYSTEM.md`

Should change from:

- one linear success path

Toward:

- generic status semantics
- clear sub-agent handoff rules
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

### Risk 5: Validation quality drops when workflow flexibility increases

**Mitigation:** require explicit validation before closure, chosen by CTO and visible in the dispatch note.

---

## Recommendation

I recommend adopting this direction.

Specifically:

1. treat the CTO as the *stateful strategic orchestrator for one product*
2. keep sub-agents *stateless and isolated*
3. redefine `status:new` as *CTO planning required*, not *engineer dispatch required*
4. introduce *workflow templates* as references, not a rigid router
5. make *validation explicit and context-dependent* instead of assuming QA is always mandatory
6. enforce active status handoff while sub-agents are working
7. require CTO to instruct sub-agents which status to set when they finish
8. store state in *recoverable artifacts*, not hidden session memory

That gives us a system that is:

- more flexible
- more product-aware
- easier to extend
- still auditable
- still automation-friendly

---

## Review Decisions

1. **Shared CTO doc + product-specific state artifacts**
   - Keep one shared CTO role/prompt/doc.
   - Product-specific state lives in per-product artifacts loaded by that shared role.
   - Product CTOs should exist as dedicated persistent named OpenClaw sessions, one per product.

2. **Keep generic review labels for now**
   - `status:review` and `status:verification` remain generic in v1.
   - Richer labels can be added later only if generic semantics become too overloaded.

3. **State artifact format stays flexible**
   - Do not hard-require JSON.
   - Provide general rules for durable, inspectable, compact state instead.

4. **All workflow templates available from day 1**
   - Feature implementation
   - Bugfix
   - Product analysis
   - UX / design
   - Trust / risk / policy
   - Content / launch

5. **Product analysis may create tickets directly**
   - Analysis is allowed to open new tickets directly when that is the correct output.
   - The CTO still owns overall orchestration afterward.

6. **Retry-limit logic remains global**
   - Keep retry/anti-loop protection at the global Board Review policy layer for now.

---

## Wake / Resume Model

The CTO does not wait for sub-agent completion.

Correct behavior:

1. the product CTO session wakes
2. CTO loads current product state + relevant project README/docs
3. CTO classifies tickets and delegates work
4. CTO records any state updates needed for continuity
5. CTO exits immediately
6. precheck detects fresh issue activity or actionable labels and wakes that same product CTO session again

How wakeup happens now:

- `skills/board-review-precheck/scripts/precheck.sh` runs every minute via OS cron / launchd
- it scans for actionable ticket states and broader issue activity
- today, it creates a fresh isolated one-shot CTO cron job from `framework/board-review/CTO_PROMPT.md`
- `watchdog.sh` resets stale WIP tickets back to `status:new` after inactivity, which also feeds the next CTO cycle

Target architecture after this redesign:

- precheck should stop creating isolated one-shot CTO sessions
- instead, it should target a persistent named session per product, for example `session:cto-churnpilot`
- each wake should enqueue one new agent turn into that product CTO session
- the CTO still exits after each pass, persistence is at the session identity layer, not the process layer

This means continuity comes from artifacts plus stable per-product session identity, not from the CTO session staying alive waiting for work.

## Context Compaction Rule

After any context compaction, the CTO must re-read:

1. the current product state artifact
2. the project `README.md`
3. any workflow template or planning doc directly relevant to the active tickets

The system should assume compaction happens. Reloading state is part of normal operation, not an exception path.

This is one reason persistent named product CTO sessions are preferable to main-session routing: compaction becomes a normal recoverable event inside a dedicated operational thread.

## Proposed Next Step

If this direction looks right, the next concrete implementation step should be:

1. define the workflow template documents
2. define the per-product state artifact rules
3. define the product-to-session mapping for persistent CTO sessions
4. rewrite `BOARD_REVIEW.md` triage so `status:new` means *classify + choose workflow + choose next role*
5. update `CTO_PROMPT.md` so every CTO wake reloads product state + project README before acting
6. update precheck so it targets named per-product CTO sessions instead of isolated one-shot CTO jobs

That lets us migrate step-by-step without forcing a risky full rewrite first.
