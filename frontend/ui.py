"""Shared presentation helpers for Streamlit views."""

from pathlib import Path

import streamlit as st


@st.cache_data(show_spinner=False)
def _load_stylesheet() -> str:
    path = Path(__file__).parent / "assets" / "style.css"
    return path.read_text(encoding="utf-8")


def inject_custom_css(theme: str = "light") -> None:
    """Load the shared stylesheet with the selected color palette."""
    palettes = {
        "light": {
            "slate": "#1E293B", "canvas": "#F8FAFC", "surface": "#FFFFFF",
            "muted": "#64748B", "line": "#E2E8F0", "sidebar": "#F1F5F9",
            "inset": "#F8FAFC", "header": "rgba(248, 250, 252, .96)",
        },
        "dark": {
            "slate": "#E2E8F0", "canvas": "#0B1220", "surface": "#151F2E",
            "muted": "#A3B3C7", "line": "#334155", "sidebar": "#101A29",
            "inset": "#0F172A", "header": "rgba(11, 18, 32, .96)",
        },
    }
    selected = palettes.get(theme, palettes["light"])
    variables = "".join(f"--{name}: {value};" for name, value in selected.items())
    st.markdown(
        f"<style>{_load_stylesheet()}\n:root {{{variables}}}</style>",
        unsafe_allow_html=True,
    )


def status_pill(label: str, variant: str = "neutral") -> str:
    """Return a small, escaped status badge suitable for Streamlit Markdown."""
    from html import escape

    allowed = {"primary", "human", "fallback", "neutral"}
    style = variant if variant in allowed else "neutral"
    return f'<span class="status-pill pill-{style}">{escape(label)}</span>'
