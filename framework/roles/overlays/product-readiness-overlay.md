# Product Readiness Auditor — ChurnPilot Overlay

## Audit Goal

Decide whether ChurnPilot is ready for broader public launch, not just whether individual features exist.

Your output should help JJ and Hendrix answer:
- Can we publish this more broadly now?
- What must be fixed before launch?
- What can wait until after launch?

## Product Context

### ChurnPilot
- **Production URL:** https://churnpilot.streamlit.app
- **Experiment URL:** https://churncopilothendrix-bc5b56cmnopm2ixz3dvhwd.streamlit.app
- **Category:** Credit card management / optimization dashboard
- **Primary value:** Help users track cards, benefits, signup bonuses, and portfolio status with less manual spreadsheet work
- **Core surfaces:** auth, card add/import, card management, dashboard insights, billing/refund comprehension, help/trust surfaces

## Audit Priorities

Focus on launch readiness across these dimensions:
1. Core functionality actually works for intended users
2. Core journeys are understandable without internal context
3. Public-facing trust is high enough
4. Operational support and deployment confidence are acceptable
5. Known issues are classified realistically

## Evidence Sources to Prefer

- Live product behavior
- Existing ChurnPilot docs and README files
- Open tickets / known issues
- QA notes and deployment notes
- Browser walkthroughs and direct observation

## Launch Recommendation Scale

Use exactly one:
- **GO** — ready for broader public exposure
- **CONDITIONAL GO** — launchable if specific fixes happen first
- **NO-GO** — too risky or incomplete for public launch

## Required Deliverable Shape

Your final answer must include:
1. Recommendation
2. Decisive reasons
3. Must-fix blockers
4. Serious but shippable risks
5. Safe-to-defer items
6. Ordered action plan
7. Confidence level

## ChurnPilot-Specific Cautions

- Do not treat internal familiarity as evidence of usability
- Documentation drift counts as launch risk if it affects support or trust
- If billing/refund messaging is inconsistent, treat that as significant
- If the app basically works but first-run comprehension is weak, do not overrate readiness
- If evidence is incomplete, say so explicitly
