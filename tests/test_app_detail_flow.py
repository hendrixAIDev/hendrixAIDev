from __future__ import annotations

import importlib
import sys
from types import ModuleType

import framework.org_view.view_model as view_model


class FakeColumn:
    def __init__(self, streamlit: "FakeStreamlit") -> None:
        self._streamlit = streamlit

    def markdown(self, value: str) -> None:
        self._streamlit.calls.append(("markdown", value))

    def caption(self, value: str) -> None:
        self._streamlit.calls.append(("caption", value))

    def code(self, value: str, language: str | None = None) -> None:
        self._streamlit.calls.append(("code", value, language))

    def write(self, value: str) -> None:
        self._streamlit.calls.append(("write", value))

    def metric(self, label: str, value: str) -> None:
        self._streamlit.calls.append(("metric", label, value))

    def button(self, label: str, **kwargs) -> bool:
        return self._streamlit.button(label, **kwargs)

    def container(self, border: bool = False) -> "FakeColumn":
        self._streamlit.calls.append(("container", border))
        return self

    def __enter__(self) -> "FakeColumn":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class FakeStreamlit:
    def __init__(self) -> None:
        self.query_params: dict[str, str] = {}
        self.clicked_keys: set[str] = set()
        self.calls: list[tuple] = []

    def set_page_config(self, **kwargs) -> None:
        self.calls.append(("set_page_config", kwargs))

    def title(self, value: str) -> None:
        self.calls.append(("title", value))

    def caption(self, value: str) -> None:
        self.calls.append(("caption", value))

    def info(self, value: str) -> None:
        self.calls.append(("info", value))

    def write(self, value: str) -> None:
        self.calls.append(("write", value))

    def divider(self) -> None:
        self.calls.append(("divider",))

    def subheader(self, value: str) -> None:
        self.calls.append(("subheader", value))

    def markdown(self, value: str) -> None:
        self.calls.append(("markdown", value))

    def columns(self, spec, gap: str = "small") -> list[FakeColumn]:
        count = spec if isinstance(spec, int) else len(spec)
        self.calls.append(("columns", count, gap))
        return [FakeColumn(self) for _ in range(count)]

    def button(self, label: str, **kwargs) -> bool:
        key = kwargs.get("key")
        self.calls.append(("button", label, key))
        clicked = key in self.clicked_keys
        if clicked and kwargs.get("on_click") is not None:
            kwargs["on_click"](*(kwargs.get("args") or ()))
        return clicked


def _load_app(monkeypatch, fake_st: FakeStreamlit):
    streamlit_module = ModuleType("streamlit")
    for name in (
        "set_page_config",
        "title",
        "caption",
        "info",
        "write",
        "divider",
        "subheader",
        "markdown",
        "columns",
        "button",
    ):
        setattr(streamlit_module, name, getattr(fake_st, name))
    streamlit_module.query_params = fake_st.query_params
    monkeypatch.setitem(sys.modules, "streamlit", streamlit_module)
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def test_main_renders_churnpilot_detail_from_query_param(monkeypatch) -> None:
    fake_st = FakeStreamlit()
    fake_st.query_params["product"] = "churnpilot"
    app = _load_app(monkeypatch, fake_st)

    detail_calls = []
    monkeypatch.setattr(
        view_model,
        "build_org_view",
        lambda _: {
            "rows": [{"product_key": "churnpilot", "detail_page_available": True}],
            "source_banner": None,
            "churnpilot_detail": {"product_key": "churnpilot"},
        },
    )
    monkeypatch.setattr(app, "_render_row", lambda row: None)
    monkeypatch.setattr(app, "_render_churnpilot_detail", lambda detail: detail_calls.append(detail))

    app.main()

    assert detail_calls == [{"product_key": "churnpilot"}]


def test_main_keeps_non_churnpilot_products_on_summary(monkeypatch) -> None:
    fake_st = FakeStreamlit()
    fake_st.query_params["product"] = "framework"
    app = _load_app(monkeypatch, fake_st)

    detail_calls = []
    monkeypatch.setattr(
        view_model,
        "build_org_view",
        lambda _: {
            "rows": [{"product_key": "framework", "detail_page_available": False}],
            "source_banner": None,
            "churnpilot_detail": {"product_key": "churnpilot"},
        },
    )
    monkeypatch.setattr(app, "_render_row", lambda row: None)
    monkeypatch.setattr(app, "_render_churnpilot_detail", lambda detail: detail_calls.append(detail))

    app.main()

    assert detail_calls == []


def test_render_row_view_detail_sets_query_param(monkeypatch) -> None:
    fake_st = FakeStreamlit()
    fake_st.clicked_keys.add("detail-churnpilot")
    app = _load_app(monkeypatch, fake_st)

    app._render_row(
        {
            "product_name": "ChurnPilot",
            "product_key": "churnpilot",
            "repo": "hendrixAIDev/churn_copilot_hendrix",
            "normalized_stage_group": "Done",
            "actionability_signal": "idle",
            "current_status_text": "No open actionable tickets.",
            "next_attention_text": "No immediate action.",
            "open_actionable_ticket_count": 0,
            "open_actionable_ticket_text": "0",
            "detail_page_available": True,
            "source_confidence_note": "direct from current state sources",
        }
    )

    assert fake_st.query_params["product"] == "churnpilot"


def test_render_churnpilot_detail_back_button_clears_query_param(monkeypatch) -> None:
    fake_st = FakeStreamlit()
    fake_st.query_params["product"] = "churnpilot"
    fake_st.clicked_keys.add("detail-back")
    app = _load_app(monkeypatch, fake_st)

    app._render_churnpilot_detail(
        {
            "product_name": "ChurnPilot",
            "detail_scope_label": "MVP 1 pilot detail page",
            "normalized_stage_group": "Done",
            "open_actionable_ticket_count": None,
            "repo": "hendrixAIDev/churn_copilot_hendrix",
            "task_queue": None,
            "snapshot_source": "Backed by product state.",
            "snapshot_timestamp_text": "Latest source timing: precheck 2026-05-16 06:06 UTC.",
            "active_issue_titles": [],
            "active_issue_context_note": "Live GitHub ticket detail is unavailable, so this section only reflects cached ticket context.",
            "current_status_text": "No current status text available from product state or tickets.",
            "stage_summary_text": "Current ticket and queue state report no open actionable work.",
            "next_attention_text": "No immediate action is visible from current product and ticket state.",
            "open_actionable_ticket_text": "unknown",
            "role_chips": [
                {
                    "role_name": "CTO",
                    "role_state": "idle",
                    "role_state_reason": "No direct evidence of active work for this role appears in the current state sources.",
                    "role_source_note": "Inferred from queue and product-state context because no direct active dispatch is present.",
                }
            ],
            "source_fidelity_note": "ticket state cached; detail view is intentionally read-only",
            "normalized_stage_legend": ["Blocked", "Ready for CTO", "Done"],
            "raw_status_context": "Latest source timing: precheck 2026-05-16 06:06 UTC.",
        }
    )

    assert "product" not in fake_st.query_params


def test_render_churnpilot_detail_keeps_provenance_with_active_issue_titles(monkeypatch) -> None:
    fake_st = FakeStreamlit()
    app = _load_app(monkeypatch, fake_st)

    app._render_churnpilot_detail(
        {
            "product_name": "ChurnPilot",
            "detail_scope_label": "MVP 1 pilot detail page",
            "normalized_stage_group": "Doing",
            "open_actionable_ticket_count": 2,
            "repo": "hendrixAIDev/churn_copilot_hendrix",
            "task_queue": "frontend",
            "snapshot_source": "Backed by product state.",
            "snapshot_timestamp_text": "Latest source timing: precheck 2026-05-16 06:06 UTC.",
            "active_issue_titles": [
                "#34 Make MVP 1 org-view source provenance explicit",
                "#35 Verify sparse-state messaging",
            ],
            "active_issue_context_note": "Issue titles come from current actionable GitHub ticket state.",
            "current_status_text": "Frontend review fix is active.",
            "stage_summary_text": "Current ticket and queue state show active work in progress.",
            "next_attention_text": "Review the active issue evidence and merge after validation.",
            "open_actionable_ticket_text": "2",
            "role_chips": [
                {
                    "role_name": "Frontend Engineer",
                    "role_state": "active",
                    "role_state_reason": "Active ticket context is present.",
                    "role_source_note": "Directly inferred from current actionable ticket state.",
                }
            ],
            "source_fidelity_note": "ticket state cached; detail view is intentionally read-only",
            "normalized_stage_legend": ["Blocked", "Ready for CTO", "Done"],
            "raw_status_context": "Latest source timing: precheck 2026-05-16 06:06 UTC.",
        }
    )

    assert ("write", "- #34 Make MVP 1 org-view source provenance explicit") in fake_st.calls
    assert ("write", "- #35 Verify sparse-state messaging") in fake_st.calls
    assert (
        "caption",
        "Issue titles come from current actionable GitHub ticket state.",
    ) in fake_st.calls
