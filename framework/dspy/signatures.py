"""DSPy Signatures for Board Review Pipeline Optimization.

Each signature defines the input/output contract for one pipeline stage.
Used by compile.py to optimize prompts against labeled quality data.
"""

try:
    import dspy
except ImportError:
    raise ImportError(
        "DSPy not installed. Run: pip install dspy-ai"
    )


class CodeReviewSignature(dspy.Signature):
    """Review code changes for a GitHub ticket and produce a verdict with findings."""

    ticket_body: str = dspy.InputField(
        desc="GitHub issue body with requirements and acceptance tests"
    )
    diff: str = dspy.InputField(
        desc="git diff of changes (experiment..branch)"
    )
    conventions: str = dspy.InputField(
        desc="CONVENTIONS.md — project coding standards"
    )
    lint_output: str = dspy.InputField(
        desc="ruff check output on changed files (empty = clean)"
    )
    streamlit_gotchas: str = dspy.InputField(
        desc="Known Streamlit pitfalls from knowledge/streamlit-gotchas.md"
    )

    verdict: str = dspy.OutputField(
        desc="APPROVE or REJECT"
    )
    findings: str = dspy.OutputField(
        desc="List of findings with severity (P1=blocker, P2=should-fix, P3=suggestion)"
    )
    scope_check: str = dspy.OutputField(
        desc="PASS if changes stay within ticket scope, FAIL with explanation if not"
    )
    review_comment: str = dspy.OutputField(
        desc="GitHub comment to post on the ticket"
    )


class EngineerSignature(dspy.Signature):
    """Implement a fix or feature for a GitHub ticket."""

    ticket_body: str = dspy.InputField(
        desc="GitHub issue body with requirements and acceptance tests"
    )
    codebase_context: str = dspy.InputField(
        desc="Relevant source files, imports, and project structure"
    )
    conventions: str = dspy.InputField(
        desc="CONVENTIONS.md — project coding standards"
    )
    streamlit_gotchas: str = dspy.InputField(
        desc="Known Streamlit pitfalls (empty string if non-Streamlit project)"
    )
    engineer_role: str = dspy.InputField(
        desc="fullstack, backend, or frontend — determines focus areas"
    )

    implementation_plan: str = dspy.OutputField(
        desc="Brief plan: what to change, why, and expected impact"
    )
    code_changes: str = dspy.OutputField(
        desc="Files modified/created with the actual code changes"
    )
    tests: str = dspy.OutputField(
        desc="Test files matching the ticket's acceptance criteria"
    )
    commit_message: str = dspy.OutputField(
        desc="Conventional commit message (e.g., fix(auth): resolve session leak)"
    )


class QASignature(dspy.Signature):
    """Verify a ticket implementation by merging to experiment and testing."""

    ticket_body: str = dspy.InputField(
        desc="GitHub issue body with acceptance tests"
    )
    code_review_comment: str = dspy.InputField(
        desc="Code reviewer's approval comment with any notes"
    )
    diff: str = dspy.InputField(
        desc="git diff of the changes being merged"
    )
    test_output: str = dspy.InputField(
        desc="pytest output after running the full test suite"
    )

    merge_safe: str = dspy.OutputField(
        desc="YES if safe to merge, NO with reason if not"
    )
    verification_report: str = dspy.OutputField(
        desc="Structured QA report: tests run, regressions, browser verification results"
    )
    bugs_found: str = dspy.OutputField(
        desc="List of bugs found during verification (empty if none)"
    )
    qa_verdict: str = dspy.OutputField(
        desc="PASS or FAIL with details"
    )


class TriageSignature(dspy.Signature):
    """Triage a new ticket: classify, add acceptance tests, dispatch the right engineer."""

    ticket_body: str = dspy.InputField(
        desc="GitHub issue body"
    )
    ticket_labels: str = dspy.InputField(
        desc="Current labels on the ticket"
    )
    evolver_matches: str = dspy.InputField(
        desc="EvoMap capsule matches for known solutions (empty if none)"
    )
    dependency_status: str = dspy.InputField(
        desc="Status of dependency tickets (all closed, or which are blocking)"
    )
    project_type: str = dspy.InputField(
        desc="Project type: streamlit, cli, api, library"
    )

    acceptance_tests: str = dspy.OutputField(
        desc="3-5 named acceptance test cases for TDD"
    )
    engineer_role: str = dspy.OutputField(
        desc="fullstack, backend, or frontend"
    )
    dispatch_note: str = dspy.OutputField(
        desc="Brief dispatch comment for the ticket"
    )
    priority_assessment: str = dspy.OutputField(
        desc="Priority level and reasoning"
    )
