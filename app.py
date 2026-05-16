"""Streamlit entrypoint for the Framework org-view MVP 1 summary."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

import streamlit as st

_RELOAD_MODULES = [
    "framework.org_view.source_data",
    "framework.org_view.view_model",
]

for module_name in _RELOAD_MODULES:
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])


def _render_row(row: dict) -> None:
    detail_label = "MVP 1 detail" if row["detail_page_available"] else "Summary only"
    ticket_count = row["open_actionable_ticket_count"]
    ticket_text = "n/a" if ticket_count is None else str(ticket_count)

    cols = st.columns([1.25, 1.15, 0.95, 1.05, 2.1, 2.0, 0.9, 1.5, 0.95], gap="small")
    cols[0].markdown("**" + str(row["product_name"]) + "**")
    cols[0].caption(str(row["product_key"]))
    cols[1].code(str(row["repo"]), language=None)
    cols[2].write(str(row["normalized_stage_group"]))
    cols[3].write(str(row["actionability_signal"]))
    cols[4].write(row["current_status_text"])
    cols[5].write(row["next_attention_text"])
    cols[6].write(ticket_text)
    cols[7].write(detail_label + " · " + str(row["source_confidence_note"]))
    if row["detail_page_available"]:
        cols[8].button(
            "View detail",
            key=f"detail-{row['product_key']}",
            on_click=_set_selected_product,
            args=(row["product_key"],),
            use_container_width=True,
        )
    else:
        cols[8].caption("Summary only")


def _selected_product() -> str | None:
    value = st.query_params.get("product")
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _set_selected_product(product_key: str | None) -> None:
    if product_key:
        st.query_params["product"] = product_key
        return
    if "product" in st.query_params:
        st.query_params.pop("product")


def _render_role_chip(column: Any, chip: dict) -> None:
    with column.container(border=True):
        column.caption(chip["role_name"])
        column.code(chip["role_state"], language=None)
        column.write(chip["role_state_reason"])
        column.caption(chip["role_source_note"])


def _render_churnpilot_detail(detail: dict) -> None:
    st.subheader(detail["product_name"] + " Detail")
    st.caption(detail["detail_scope_label"])
    st.button(
        "Back to summary",
        key="detail-back",
        on_click=_set_selected_product,
        args=(None,),
    )

    meta_cols = st.columns(4, gap="small")
    ticket_count = detail["open_actionable_ticket_count"]
    ticket_text = "n/a" if ticket_count is None else str(ticket_count)
    meta_cols[0].metric("Stage", detail["normalized_stage_group"])
    meta_cols[1].metric("Actionable tickets", ticket_text)
    meta_cols[2].markdown("**Repo**")
    meta_cols[2].code(str(detail["repo"]), language=None)
    meta_cols[3].markdown("**Task queue**")
    meta_cols[3].caption(str(detail["task_queue"] or "Unavailable"))

    st.info(detail["snapshot_source"])
    st.caption(detail["snapshot_timestamp_text"])

    status_cols = st.columns([1.3, 1.1], gap="large")
    status_cols[0].markdown("**Current status**")
    status_cols[0].write(detail["current_status_text"])
    status_cols[0].markdown("**Active issue context**")
    if detail["active_issue_titles"]:
        for title in detail["active_issue_titles"]:
            status_cols[0].write("- " + title)
    else:
        status_cols[0].caption("No open actionable ChurnPilot issue titles are available from current sources.")

    status_cols[1].markdown("**Stage summary**")
    status_cols[1].write(detail["stage_summary_text"])
    status_cols[1].markdown("**Next attention**")
    status_cols[1].write(detail["next_attention_text"])

    st.markdown("**Role chips**")
    role_cols = st.columns(len(detail["role_chips"]), gap="small")
    for column, chip in zip(role_cols, detail["role_chips"]):
        _render_role_chip(column, chip)

    st.markdown("**Source fidelity**")
    st.write(detail["source_fidelity_note"])
    st.caption("Stage legend: " + " → ".join(detail["normalized_stage_legend"]))
    st.caption(detail["raw_status_context"])


def main() -> None:
    from framework.org_view.view_model import build_org_view

    st.set_page_config(
        page_title="Framework Org View",
        page_icon=":material/account_tree:",
        layout="wide",
    )
    st.title("Organization Operations Map")
    st.caption(
        "Read-only MVP 1 org summary. Sources: per-product state, product queues, and "
        "GitHub issue/status-label state or precheck cache."
    )

    summary = build_org_view(Path(__file__).resolve().parent)
    st.write(
        "Default view is org-first. ChurnPilot is the only product marked detail-enabled in MVP 1."
    )
    if summary["source_banner"]:
        st.info(summary["source_banner"])

    header = st.columns([1.25, 1.15, 0.95, 1.05, 2.1, 2.0, 0.9, 1.5, 0.95], gap="small")
    labels = [
        "Product",
        "Repo",
        "Stage",
        "Signal",
        "Current status",
        "Next attention",
        "Actionable tickets",
        "Detail + source confidence",
        "Action",
    ]
    for col, label in zip(header, labels):
        col.markdown("**" + label + "**")

    st.divider()

    for row in summary["rows"]:
        _render_row(row)
        st.divider()

    if _selected_product() == "churnpilot" and summary["churnpilot_detail"]:
        _render_churnpilot_detail(summary["churnpilot_detail"])


if __name__ == "__main__":
    main()
