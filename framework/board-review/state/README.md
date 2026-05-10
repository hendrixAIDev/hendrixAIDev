# Product State Artifacts

Location for per-product CTO state.

Shared contract:
- use `framework/board-review/state/<product>.*` or the equivalent product-local path
- compact cross-run product state only
- do not reload on every wake by default
- reload after compaction, recovery, or when an external process may have changed the artifact
- do not duplicate GitHub ticket history
- do not turn into a journal
- move durable knowledge to project docs/plans

Per-product CTO sessions will define the actual contents later.
