"""CBAM-Ready Emissions Passport - main Streamlit application."""

# Streamlit adds this script's directory to sys.path. The backend package and
# this entry point are both named ``app``; keep the repository root first so
# imports such as ``app.modules`` resolve to the backend package.
import sys
from datetime import date
from html import escape
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
FRONTEND_DIR = str(Path(__file__).resolve().parent)
sys.path[:] = [path for path in sys.path if str(Path(path or ".").resolve()) != FRONTEND_DIR]
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests
import streamlit as st

from frontend.ui import inject_custom_css
from frontend.views.allocation import render_allocation_view
from frontend.views.dashboard import render_dashboard_view
from frontend.views.rag_view import render_rag_view
from frontend.views.review import render_review_view
from frontend.views.upload import render_upload_view
from frontend.views.workspace import render_workspace_view

st.set_page_config(
    page_title="CBAM-Ready Emissions Passport",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = "http://localhost:8000"
STEPS = [
    ("workspace", "1 · Workspace"),
    ("upload", "2 · Upload"),
    ("review", "3 · Review"),
    ("allocation", "4 · Allocation"),
    ("passport", "5 · Passport"),
]


def clear_legacy_demo_state() -> None:
    """Drop the old shipped demo workspace/records from an already-open session."""
    marker = "real_data_only_cleanup_v1"
    if st.session_state.get(marker):
        return

    workspace = st.session_state.get("workspace") or {}
    if (
        workspace.get("company_name") == "Apex Fasteners Pvt Ltd"
        and workspace.get("installation_id") == "IN-FDB-001"
    ):
        st.session_state.pop("workspace", None)

    allocation = st.session_state.get("allocation_data") or {}
    if (
        allocation.get("target_production_tonnes") == 500.0
        and allocation.get("total_facility_production_tonnes") == 625.0
    ):
        st.session_state.pop("allocation_data", None)

    demo_names = {
        "DHBVN_Electricity_Oct2026.csv",
        "IOCL_Furnace_Oil_Invoice.csv",
        "Steel_Wire_Rod_Mill_Cert.csv",
        "Factory_Production_Summary.csv",
    }
    documents = st.session_state.get("uploaded_documents") or {}
    removed_hashes = {
        digest for digest, document in documents.items()
        if document.get("filename") in demo_names
    }
    if removed_hashes:
        st.session_state["uploaded_documents"] = {
            digest: document for digest, document in documents.items()
            if digest not in removed_hashes
        }
        overrides = st.session_state.get("field_overrides") or {}
        st.session_state["field_overrides"] = {
            key: value for key, value in overrides.items()
            if not any(key.startswith(f"{digest}_") for digest in removed_hashes)
        }
        st.session_state.pop("latest_calculation", None)

    st.session_state[marker] = True


def check_api_health() -> bool:
    try:
        return requests.get(f"{API_BASE_URL}/health", timeout=1).status_code == 200
    except requests.RequestException:
        return False


def step_completion() -> dict[str, bool]:
    """Which workflow steps already have the data they are responsible for."""
    state = st.session_state
    return {
        "workspace": bool(state.get("workspace")),
        "upload": bool(state.get("uploaded_documents")),
        "review": bool(state.get("uploaded_documents")) and bool(state.get("review_visited")),
        "allocation": bool(state.get("allocation_data")),
        "passport": bool(state.get("latest_calculation")),
    }


def _install_row(label: str, value: str | None, placeholder: str) -> str:
    if value:
        return f'<div class="install-row"><span>{escape(label)}</span><b>{escape(str(value))}</b></div>'
    return f'<div class="install-row"><span>{escape(label)}</span><b class="unset">{escape(placeholder)}</b></div>'


def _short_period(workspace: dict) -> str | None:
    """'2026-10-01'..'2026-10-31' -> '1 Oct – 31 Oct 2026' so it fits the sidebar card."""
    try:
        start = date.fromisoformat(workspace["start_date"])
        end = date.fromisoformat(workspace["end_date"])
    except (KeyError, TypeError, ValueError):
        return workspace.get("reporting_period")
    if start.year == end.year:
        return f"{start.day} {start:%b} – {end.day} {end:%b %Y}"
    return f"{start.day} {start:%b %Y} – {end.day} {end:%b %Y}"


def render_sidebar(active_page: str) -> None:
    with st.sidebar:
        st.markdown(
            '<div class="brand"><div class="brand-mark">🌿</div><div>'
            '<div class="brand-name">CBAM Passport</div>'
            '<div class="brand-sub">Embedded-emissions evidence workspace</div></div></div>',
            unsafe_allow_html=True,
        )
        if check_api_health():
            st.markdown(
                '<div class="conn conn-on"><span class="conn-dot"></span><div>Backend connected'
                '<small>Overrides sync to the audit ledger</small></div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="conn conn-off"><span class="conn-dot"></span><div>Local mode'
                '<small>Backend offline · calculations run in-app</small></div></div>',
                unsafe_allow_html=True,
            )

        st.write("")
        if st.button(
            "💬  Regulatory Assistant",
            use_container_width=True,
            type="primary" if active_page == "rag" else "secondary",
        ):
            st.session_state["active_page"] = "rag"
            st.rerun()

        workspace = st.session_state.get("workspace", {})
        st.markdown('<div class="side-label" style="margin-top:18px">Active installation</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="install-card">'
            + _install_row("Entity", workspace.get("company_name"), "Not configured")
            + _install_row("Plant", workspace.get("installation_name"), "Not configured")
            + _install_row("CN code", workspace.get("cn_code"), "Not selected")
            + _install_row("Period", _short_period(workspace), "Not set")
            + _install_row("Documents", str(len(st.session_state.get("uploaded_documents", {}))), "0")
            + "</div>",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="side-label" style="margin-top:18px">Appearance</div>', unsafe_allow_html=True)
        st.toggle("Dark mode", key="dark_mode", help="Switch the workspace between light and dark appearance.")
        st.divider()
        st.markdown(
            '<div class="side-foot">Decision-support prototype. Does not certify emissions '
            'or replace an accredited verifier.</div>',
            unsafe_allow_html=True,
        )


def render_step_nav(active_page: str) -> None:
    done = step_completion()
    completed = sum(done.values())
    st.markdown(
        '<div class="hero"><div><div class="hero-title">CBAM Emissions Passport</div>'
        '<div class="hero-sub">From raw invoices to a verifier-ready embedded-emissions declaration</div></div>'
        '<div class="hero-tags"><span class="hero-tag">Steel fasteners pilot</span>'
        '<span class="hero-tag">SHA-256 evidence</span><span class="hero-tag">Monte Carlo uncertainty</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="progress-meta"><span>Workflow</span><span>{completed} of {len(STEPS)} steps complete</span></div>',
        unsafe_allow_html=True,
    )
    with st.container(key="stepnav"):
        step_columns = st.columns(len(STEPS), gap="small")
        for column, (step_id, label) in zip(step_columns, STEPS):
            prefix = "✓ " if done[step_id] and active_page != step_id else ""
            with column:
                if st.button(
                    prefix + label,
                    key=f"step_{step_id}",
                    use_container_width=True,
                    type="primary" if active_page == step_id else "secondary",
                ):
                    st.session_state["active_page"] = step_id
                    st.rerun()


def main() -> None:
    clear_legacy_demo_state()
    active_page = st.session_state.setdefault("active_page", "workspace")

    render_sidebar(active_page)
    inject_custom_css("dark" if st.session_state.get("dark_mode", False) else "light")
    render_step_nav(active_page)

    active_page = st.session_state.get("active_page", "workspace")
    if active_page == "workspace":
        render_workspace_view()
    elif active_page == "upload":
        render_upload_view()
    elif active_page == "review":
        render_review_view()
    elif active_page == "allocation":
        render_allocation_view()
    elif active_page == "passport":
        render_dashboard_view()
    elif active_page == "rag":
        render_rag_view()


if __name__ == "__main__":
    main()
