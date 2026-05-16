"""Streamlit entrypoint for the Framework org-view MVP 1 summary."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import streamlit as st

_RELOAD_MODULES = [
    "framework.org_view.source_data",
    "framework.org_view.view_model",
]

for module_name in _RELOAD_MODULES:
    if module_name in sys.modules:
        importlib.reload(sys.modules[module_name])

from framework.org_view.view_model import build_org_summary


def _render_row(row: dict) -> None:
    detail_label = "MVP 1 detail" if row["detail_page_available"] else "Summary only"
    ticket_count = row["open_actionable_ticket_count"]
    ticket_text = "n/a" if ticket_count is None else str(ticket_count)

    cols = st.columns([1.35, 1.25, 1, 1.1, 2.2, 2.1, 1, 1.8], gap="small")
    cols[0].markdown("**" + str(row["product_name"]) + "**")
    cols[0].caption(str(row["product_key"]))
    cols[1].code(str(row["repo"]), language=None)
    cols[2].write(str(row["normalized_stage_group"]))
    cols[3].write(str(row["actionability_signal"]))
    cols[4].write(row["current_status_text"])
    cols[5].write(row["next_attention_text"])
    cols[6].write(ticket_text)
    cols[7].write(detail_label + " · " + str(row["source_confidence_note"]))


def main() -> None:
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

    summary = build_org_summary(Path(__file__).resolve().parent)
    st.write(
        "Default view is org-first. ChurnPilot is the only product marked detail-enabled in MVP 1."
    )
    if summary["source_banner"]:
        st.info(summary["source_banner"])

    header = st.columns([1.35, 1.25, 1, 1.1, 2.2, 2.1, 1, 1.8], gap="small")
    labels = [
        "Product",
        "Repo",
        "Stage",
        "Signal",
        "Current status",
        "Next attention",
        "Actionable tickets",
        "Detail + source confidence",
    ]
    for col, label in zip(header, labels):
        col.markdown("**" + label + "**")

    st.divider()

    for row in summary["rows"]:
        _render_row(row)
        st.divider()


if __name__ == "__main__":
    main()
