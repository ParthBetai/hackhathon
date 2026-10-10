"""Optional source review, deliberately separate from numerical scenario inputs."""

import os

import streamlit as st

from commonroot.contracts import ModelError
from commonroot.evidence import confirm_evidence, extract_event
from commonroot.service import RunBundle


def render_evidence(bundle: RunBundle) -> None:
    st.subheader("Source review")
    st.caption("Optional Gemini extraction. Manual scenarios and all numerical calculations work without it.")
    configured = bool(os.environ.get("GEMINI_API_KEY")) and bool(os.environ.get("GEMINI_MODEL"))
    if not configured:
        st.info("Gemini is not configured. Set GEMINI_API_KEY and GEMINI_MODEL in the server environment to enable extraction. Nothing below blocks Run simulation.")
    else:
        st.caption(f"Provider: Google Gemini · configured model: {os.environ['GEMINI_MODEL']}")
    text = st.text_area("Source excerpt", max_chars=20000, height=160, key="evidence_excerpt",
                        help="Do not include credentials or personal data. Extraction sends this excerpt to Google only when requested.")
    url = st.text_input("Source URL (optional)", key="evidence_url", placeholder="https://…")
    consent = st.checkbox("Send this excerpt to the configured Gemini model for reference-only extraction.", key="evidence_consent")
    if st.button("Extract source facts", disabled=not configured or not consent):
        try:
            with st.spinner("Extracting literal source facts; no model inputs will change…"):
                candidate = extract_event(text, url or None)
        except ModelError as exc:
            st.error(f"{exc.code}: {exc}")
            st.session_state.pop("evidence_candidate", None)
        else:
            st.session_state["evidence_candidate"] = candidate
            st.session_state["evidence_candidate_source"] = (text, url)
    candidate = st.session_state.get("evidence_candidate")
    if candidate:
        current = st.session_state.get("evidence_candidate_source") == (text, url)
        st.json(candidate.model_dump(mode="json"), expanded=True)
        if not current:
            st.warning("Source changed. Extract again before saving a reference.")
        reviewed = st.checkbox("I reviewed these quotes. Save the excerpt as a reference in my next run; do not apply model parameters.", key="evidence_review")
        if st.button("Save reviewed reference for next run", disabled=not current or not reviewed):
            try:
                record = confirm_evidence(candidate, text)
            except ModelError as exc:
                st.error(f"{exc.code}: {exc}")
            else:
                st.session_state["confirmed_evidence"] = [record]
                st.success("Reference queued. It will be stored only when you run a new simulation. Enter affected IDs, dates and impact manually in the scenario desk.")
    pending = st.session_state.get("confirmed_evidence", [])
    if pending:
        st.caption("A reviewed reference is queued for the next simulation. Its excerpt will be retained in local run history and exports.")
        if st.button("Remove queued reference"):
            st.session_state["confirmed_evidence"] = []
            st.rerun()
    if bundle.evidence:
        with st.expander("References attached to the displayed run"):
            st.json(bundle.evidence)
    else:
        st.caption("No source evidence attached to the displayed run. Its disruption is a user-entered synthetic assumption, not a reported fact.")
