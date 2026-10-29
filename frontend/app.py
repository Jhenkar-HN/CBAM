"""CBAM-Ready Emissions Passport - main Streamlit application."""

# Streamlit adds this script's directory to sys.path. The backend package and
# this entry point are both named ``app``; keep the repository root first so
# imports such as ``app.modules`` resolve to the backend package.
import sys
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
    ("workspace", "1 · Setup Workspace"),
    ("upload", "2 · Upload Records"),
    ("review", "3 · Review & Override"),
    ("allocation", "4 · Mass Allocation"),
    ("passport", "5 · Emissions Passport"),
]


def check_api_health() -> bool:
    try:
        return requests.get(f"{API_BASE_URL}/health", timeout=1).status_code == 200
    except requests.RequestException:
        return False


def main() -> None:
    active_page = st.session_state.setdefault("active_page", "workspace")

    with st.sidebar:
        st.title("CBAM Passport")
        st.caption("Decision-support workspace for CBAM evidence preparation")
        if check_api_health():
            st.success("Backend API connected")
        else:
            st.info("Backend unavailable · local calculation mode")

        st.toggle("Dark mode", key="dark_mode", help="Switch the workspace between light and dark appearance.")

        if st.button(
            "Regulatory Assistant",
            use_container_width=True,
            type="primary" if active_page == "rag" else "secondary",
        ):
            st.session_state["active_page"] = "rag"
            st.rerun()

        st.divider()
        workspace = st.session_state.get("workspace", {})
        st.markdown("**Active installation**")
        st.markdown(f"**Entity:** {workspace.get('company_name', 'Apex Fasteners')}")
        st.markdown(f"**Plant:** {workspace.get('installation_name', 'Apex Unit 1')}")
        st.markdown(f"**CN code:** {workspace.get('cn_code', '7318 15 82')}")
        st.markdown(f"**Ledger documents:** {len(st.session_state.get('uploaded_documents', {}))}")
        st.divider()
        st.caption("Decision-support prototype. Does not certify emissions or replace an accredited verifier.")

    inject_custom_css("dark" if st.session_state.get("dark_mode", False) else "light")

    st.markdown(
        '<div class="audit-callout"><b>CBAM Emissions Passport</b> · Steel Fasteners pilot · '
        'SHA-256 evidence traceability</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    step_columns = st.columns(5, gap="small")
    for column, (step_id, label) in zip(step_columns, STEPS):
        with column:
            if st.button(
                label,
                key=f"step_{step_id}",
                use_container_width=True,
                type="primary" if active_page == step_id else "secondary",
            ):
                st.session_state["active_page"] = step_id
                st.rerun()

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
