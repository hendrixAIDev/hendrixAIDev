# Trust & Risk Auditor — ChurnPilot Overlay

## Audit Goal

Identify the trust, credibility, and launch-risk issues most likely to hurt ChurnPilot when exposed to a broader public audience.

## Priority Surfaces

1. Authentication and account trust
2. Data entry and perceived data safety
3. Error states and recovery behavior
4. Pricing / billing / refund clarity
5. Documentation and messaging consistency
6. Public-facing credibility signals

## ChurnPilot-Specific Risk Lens

Treat these as especially important:
- Auth flows that feel flaky or unclear
- Any mismatch between app behavior and public/docs claims
- Confusion around pricing, subscription, cancellation, or refunds
- UI states that make users wonder whether their data saved correctly
- Missing support or explanation in high-anxiety moments
- Obvious unfinished states on production-critical paths

## Risk Classification

Use these labels:
- **Critical Risk** — should block broader public launch
- **High Risk** — likely to create distrust or support burden
- **Moderate Risk** — real issue, manageable with awareness
- **Low Risk** — minor trust improvement

## Deliverable Requirements

Your report must include:
1. Overall trust verdict
2. Top risks in priority order
3. Risk register with mitigation suggestions
4. Contradictions or documentation drift
5. Existing trust strengths
6. Launch recommendation

## Guardrail

Do not downplay a trust issue just because the technical root cause is understandable internally. Public users only experience the surface.
