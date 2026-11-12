"""Shared presentation helpers for Streamlit views."""

from html import escape
from pathlib import Path

import streamlit as st

PALETTES = {
    "light": {
        "slate": "#0F172A", "canvas": "#F6F8FA", "surface": "#FFFFFF",
        "muted": "#64748B", "line": "#E2E8F0", "sidebar": "#FFFFFF",
        "inset": "#F8FAFC", "header": "rgba(246, 248, 250, .96)",
        "info-bg": "#EFF6FF", "info-line": "#BFDBFE", "info-fg": "#1E3A8A",
        "ok-bg": "#ECFDF5", "ok-line": "#A7F3D0", "ok-fg": "#065F46",
        "warn-bg": "#FFFBEB", "warn-line": "#FDE68A", "warn-fg": "#92400E",
        "err-bg": "#FEF2F2", "err-line": "#FECACA", "err-fg": "#991B1B",
    },
    "dark": {
        "slate": "#E2E8F0", "canvas": "#0B1220", "surface": "#121C2C",
        "muted": "#94A3B8", "line": "#26344A", "sidebar": "#0E1726",
        "inset": "#0F172A", "header": "rgba(11, 18, 32, .96)",
        "info-bg": "rgba(37, 99, 235, .14)", "info-line": "rgba(96, 165, 250, .35)", "info-fg": "#BFDBFE",
        "ok-bg": "rgba(16, 185, 129, .14)", "ok-line": "rgba(52, 211, 153, .35)", "ok-fg": "#A7F3D0",
        "warn-bg": "rgba(217, 119, 6, .14)", "warn-line": "rgba(251, 191, 36, .35)", "warn-fg": "#FDE68A",
        "err-bg": "rgba(220, 38, 38, .14)", "err-line": "rgba(248, 113, 113, .35)", "err-fg": "#FECACA",
    },
}


@st.cache_data(show_spinner=False)
def _load_stylesheet() -> str:
    path = Path(__file__).parent / "assets" / "style.css"
    return path.read_text(encoding="utf-8")


def inject_custom_css(theme: str | None = None) -> None:
    """Load the shared stylesheet using the selected app appearance."""
    if theme is None:
        theme = "dark" if st.session_state.get("dark_mode", False) else "light"
    selected = PALETTES.get(theme, PALETTES["light"])
    variables = "".join(f"--{name}: {value};" for name, value in selected.items())
    st.markdown(
        f"<style>{_load_stylesheet()}\n:root {{{variables} color-scheme: {theme};}}</style>",
        unsafe_allow_html=True,
    )


def page_header(eyebrow: str, title: str, description: str = "") -> None:
    """Consistent heading block used at the top of every view."""
    desc = f'<div class="page-desc">{escape(description)}</div>' if description else ""
    st.markdown(
        f'<div class="page-head"><div class="page-eyebrow">{escape(eyebrow)}</div>'
        f'<div class="page-title">{escape(title)}</div>{desc}</div>',
        unsafe_allow_html=True,
    )


def empty_state(icon: str, title: str, text: str = "") -> None:
    """Friendly placeholder shown when a step has nothing to display yet."""
    body = f'<div class="es-text">{escape(text)}</div>' if text else ""
    st.markdown(
        f'<div class="empty-state"><div class="es-icon">{escape(icon)}</div>'
        f'<div class="es-title">{escape(title)}</div>{body}</div>',
        unsafe_allow_html=True,
    )


def status_pill(label: str, variant: str = "neutral") -> str:
    """Return a small, escaped status badge suitable for Streamlit Markdown."""
    allowed = {"primary", "human", "fallback", "neutral"}
    style = variant if variant in allowed else "neutral"
    return f'<span class="status-pill pill-{style}">{escape(label)}</span>'
